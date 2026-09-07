import ipaddress
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import models
from django.utils import timezone

from apps.companies.models import Company, HotspotConfiguration
from apps.entitlements.models import AccessEntitlement
from apps.entitlements.services.entitlement_services import is_entitlement_authorizable
from apps.plans.models import Plan
from apps.vouchers.models import Voucher, VoucherStatus
from apps.vouchers.services.voucher_services import redeem_voucher

logger = logging.getLogger(__name__)

# Customer-facing friendly error messages mapped by internal reason code
CUSTOMER_ERROR_MESSAGES = {
    'EN': {
        'INVALID_CODE': 'Invalid voucher code. Please check and try again.',
        'NOT_FOUND': 'Voucher not found for this network.',
        'SUSPENDED': 'This access pass has been temporarily suspended. Please contact support.',
        'REVOKED': 'This access pass is no longer valid.',
        'EXPIRED': 'This access pass has expired.',
        'DATA_QUOTA_EXHAUSTED': 'Your data allowance has been completely used.',
        'USAGE_TIME_EXHAUSTED': 'Your access time allowance has been completely used.',
        'DEVICE_LIMIT_REACHED': 'This access pass is already linked to the maximum number of devices. Please contact support if you changed your device.',
        'SESSION_LIMIT_REACHED': 'This access pass is currently in use on another active session.',
        'INACTIVE_HOTSPOT': 'This Wi-Fi HotSpot is currently inactive.',
        'GENERIC_ERROR': 'Unable to connect to the network. Please try again or contact support.'
    },
    'SW': {
        'INVALID_CODE': 'Nambari ya vocha si sahihi. Tafadhali hakiki na ujaribu tena.',
        'NOT_FOUND': 'Vocha haijapatikana kwenye mtandao huu.',
        'SUSPENDED': 'Kifurushi hiki kimesimamishwa kwa muda. Tafadhali wasiliana na huduma kwa wateja.',
        'REVOKED': 'Kifurushi hiki hakitumiki tena.',
        'EXPIRED': 'Kifurushi hiki kimeisha muda wake.',
        'DATA_QUOTA_EXHAUSTED': 'Kiasi chako cha bando la intaneti kimekwisha.',
        'USAGE_TIME_EXHAUSTED': 'Muda wako wa kutumia intaneti umekwisha.',
        'DEVICE_LIMIT_REACHED': 'Vocha hii tayari imeunganishwa na idadi ya juu ya vifaa vinavyoruhusiwa.',
        'SESSION_LIMIT_REACHED': 'Vocha hii inatumika kwa sasa kwenye kifaa kingine.',
        'INACTIVE_HOTSPOT': 'Mtandao huu wa Wi-Fi haupatikani kwa sasa.',
        'GENERIC_ERROR': 'Imeshindwa kuunganisha mtandao. Tafadhali jaribu tena au wasiliana na huduma.'
    }
}


def get_customer_error_message(reason_code: str, lang: str = 'EN') -> str:
    """Return customer-safe localized error message."""
    lang_key = 'SW' if str(lang).upper() == 'SW' else 'EN'
    return CUSTOMER_ERROR_MESSAGES[lang_key].get(
        reason_code,
        CUSTOMER_ERROR_MESSAGES[lang_key]['GENERIC_ERROR']
    )


def resolve_hotspot_by_slug(slug: str) -> Optional[HotspotConfiguration]:
    """Resolve an active HotspotConfiguration by its public slug (case-insensitive)."""
    clean_slug = (slug or '').strip()
    if not clean_slug:
        return None
    return HotspotConfiguration.objects.select_related('company', 'location', 'router').filter(
        slug__iexact=clean_slug
    ).first()


def get_default_hotspot(company: Company) -> Optional[HotspotConfiguration]:
    """
    Resolve the explicit default active HotSpot for a company.
    Falls back to first active hotspot if no explicit is_default is set.
    """
    if not company:
        return None
    return company.hotspots.filter(is_default=True, is_active=True).first() or \
           company.hotspots.filter(is_default=True).first() or \
           company.hotspots.filter(is_active=True).first()


def get_hotspot_by_slug(slug: str, company: Optional[Company] = None) -> Optional[HotspotConfiguration]:
    """Resolve a HotspotConfiguration by slug, optionally scoped to a company."""
    clean_slug = (slug or '').strip()
    if not clean_slug:
        return None
    qs = HotspotConfiguration.objects.select_related('company', 'location', 'router').filter(slug__iexact=clean_slug)
    if company:
        qs = qs.filter(company=company)
    return qs.first()


def get_hotspot_by_id(hotspot_id: Any, company: Optional[Company] = None) -> Optional[HotspotConfiguration]:
    """Resolve a HotspotConfiguration by UUID, optionally scoped to a company."""
    if not hotspot_id:
        return None
    qs = HotspotConfiguration.objects.select_related('company', 'location', 'router').filter(id=hotspot_id)
    if company:
        qs = qs.filter(company=company)
    return qs.first()


def get_plans_for_hotspot(hotspot: HotspotConfiguration, include_inactive: bool = False):
    """
    Return plans available for a HotSpot.
    If the HotSpot has explicit assigned plans, returns those.
    Otherwise, falls back to all active plans of the company for backward compatibility.
    """
    assigned_qs = hotspot.plans.all() if include_inactive else hotspot.plans.filter(is_active=True)
    if assigned_qs.exists():
        return assigned_qs.order_by('price')

    company_qs = Plan.objects.filter(company=hotspot.company)
    if not include_inactive:
        company_qs = company_qs.filter(is_active=True)
    return company_qs.order_by('price')


def get_or_create_default_hotspot(company: Company) -> HotspotConfiguration:
    """
    DEPRECATED: Backward-compatibility wrapper for legacy callers.
    Resolves the company's designated default HotSpot without side-effect creation if exists.
    """
    hotspot = get_default_hotspot(company)
    if not hotspot:
        slug = company.slug or f"hotspot-{company.id.hex[:6]}"
        hotspot = HotspotConfiguration.objects.create(
            company=company,
            name=f"{company.name} HotSpot",
            slug=slug,
            ssid=f"{company.name} Wi-Fi",
            brand_name=company.name,
            headline="Welcome to High-Speed Wi-Fi",
            welcome_text="Enter your access voucher code below to start browsing.",
            primary_color="#2563eb",
            is_default=True,
            is_active=True
        )
    return hotspot



PORTAL_CONTEXT_SALT = 'usimamizi-portal-context-v1'


def validate_handoff_login_url(url: str, hotspot: HotspotConfiguration) -> Optional[str]:
    """
    Validate that a runtime handoff URL (e.g. MikroTik link-login) is safe and points
    to the expected router/gateway for this hotspot.
    """
    if not url or not isinstance(url, str):
        return None

    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception:
        return None

    # Enforce safe scheme
    if parsed.scheme.lower() not in ('http', 'https'):
        return None

    hostname = parsed.hostname
    if not hostname:
        return None

    hostname_lower = hostname.lower()

    # Disallow cloud metadata and loopback abuse
    if hostname_lower in ('169.254.169.254', 'metadata.google.internal', 'localhost'):
        return None

    # Check against hotspot configured targets
    allowed_hosts = set()
    if hotspot.gateway_ip:
        allowed_hosts.add(hotspot.gateway_ip.strip().lower())

    if hotspot.router and hotspot.router.management_ip:
        allowed_hosts.add(hotspot.router.management_ip.strip().lower())

    if hotspot.router_login_url:
        try:
            cfg_parsed = urlparse(hotspot.router_login_url.strip())
            if cfg_parsed.hostname:
                allowed_hosts.add(cfg_parsed.hostname.lower())
        except Exception:
            pass

    if hostname_lower in allowed_hosts:
        return clean_url

    # Check if hostname is an IP in private IP ranges (RFC 1918)
    try:
        ip_obj = ipaddress.ip_address(hostname_lower)
        if ip_obj.is_private and not ip_obj.is_loopback and not ip_obj.is_link_local:
            if hotspot.gateway_ip:
                try:
                    gw_ip = ipaddress.ip_address(hotspot.gateway_ip.strip())
                    gw_network = ipaddress.ip_network(f"{gw_ip}/24", strict=False)
                    if ip_obj in gw_network:
                        return clean_url
                except Exception:
                    pass
            else:
                return clean_url
    except ValueError:
        pass

    logger.warning("Rejected unverified handoff URL: %s for hotspot %s", clean_url, hotspot.slug)
    return None


def validate_destination_url(url: str, portal_host: Optional[str] = None) -> str:
    """
    Validate post-auth redirect target (e.g. link-orig or dst) to protect against
    open redirects and captive portal loops.
    """
    default_dst = "https://www.google.com"
    if not url or not isinstance(url, str):
        return default_dst

    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception:
        return default_dst

    if parsed.scheme.lower() not in ('http', 'https'):
        return default_dst

    hostname = (parsed.hostname or '').lower()

    # Prevent loop back to portal
    if portal_host and hostname == portal_host.lower():
        return default_dst

    # Prevent portal path loop
    if '/p/' in parsed.path:
        return default_dst

    return clean_url


def get_hotspot_login_url(
    hotspot: HotspotConfiguration,
    runtime_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Derive the definitive RouterOS login handoff URL using the 3-tier precedence:
    1. Validated runtime link-login from runtime_context (e.g. passed from MikroTik query param)
    2. Configured hotspot router_login_url override
    3. Derived gateway URL: http://{hotspot.gateway_ip}/login (if gateway_ip is present)
    4. Legacy safety fallback: http://10.5.50.1/login
    """
    # 1. Check runtime context
    if runtime_context:
        candidate = (
            runtime_context.get('link-login') or
            runtime_context.get('link-login-only') or
            runtime_context.get('link_login')
        )
        if candidate:
            validated = validate_handoff_login_url(str(candidate), hotspot)
            if validated:
                return validated

    # 2. Configured override vs 3. Derived gateway
    configured_url = (hotspot.router_login_url or '').strip()
    if hotspot.gateway_ip:
        gw_ip = hotspot.gateway_ip.strip()
        derived_url = f"http://{gw_ip}/login"
        if configured_url and configured_url != 'http://10.5.50.1/login':
            return configured_url
        if gw_ip != '10.5.50.1' and configured_url == 'http://10.5.50.1/login':
            return derived_url
        if configured_url:
            return configured_url
        return derived_url

    if configured_url:
        return configured_url

    return 'http://10.5.50.1/login'


def create_signed_portal_context(
    hotspot: HotspotConfiguration,
    runtime_params: Optional[Dict[str, Any]] = None
) -> str:
    """Create a tamper-resistant signed portal context token."""
    signer = TimestampSigner(salt=PORTAL_CONTEXT_SALT)
    params = runtime_params or {}

    link_login = params.get('link-login') or params.get('link-login-only') or params.get('link_login') or ''
    validated_link_login = validate_handoff_login_url(str(link_login), hotspot) if link_login else ''

    link_orig = params.get('link-orig') or params.get('dst') or params.get('link_orig') or ''
    validated_link_orig = validate_destination_url(str(link_orig)) if link_orig else 'https://www.google.com'

    payload = {
        'hotspot_id': str(hotspot.id),
        'hotspot_slug': hotspot.slug,
        'router_id': str(hotspot.router_id) if hotspot.router_id else None,
        'location_id': str(hotspot.location_id) if hotspot.location_id else None,
        'gateway_ip': hotspot.gateway_ip or '',
        'link_login': validated_link_login,
        'link_orig': validated_link_orig,
        'mac': (str(params.get('mac') or '')).strip().upper(),
        'ip': (str(params.get('ip') or '')).strip(),
        'issued_at': timezone.now().isoformat(),
    }
    token = signer.sign(json.dumps(payload))
    logger.info("PORTAL_CONTEXT_CREATED: hotspot=%s gateway=%s mac=%s", hotspot.slug, hotspot.gateway_ip, payload['mac'])
    return token


def verify_signed_portal_context(
    token: str,
    hotspot: HotspotConfiguration,
    max_age: int = 3600
) -> Optional[Dict[str, Any]]:
    """Verify and decode a signed portal context token."""
    if not token:
        return None
    signer = TimestampSigner(salt=PORTAL_CONTEXT_SALT)
    try:
        raw_json = signer.unsign(token, max_age=max_age)
        payload = json.loads(raw_json)
        if payload.get('hotspot_id') != str(hotspot.id):
            logger.warning("Portal context token hotspot_id mismatch: %s != %s", payload.get('hotspot_id'), hotspot.id)
            return None
        return payload
    except SignatureExpired:
        logger.info("Portal context token expired for hotspot %s", hotspot.slug)
        return None
    except (BadSignature, Exception) as exc:
        logger.warning("Invalid portal context token for hotspot %s: %s", hotspot.slug, exc)
        return None


def validate_and_redeem_portal_voucher(
    *,
    hotspot: HotspotConfiguration,
    voucher_code: str,
    customer_phone: Optional[str] = None,
    lang: str = 'EN',
    runtime_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate a customer-entered voucher on the public captive portal.
    Atomically redeems AVAILABLE vouchers or validates existing REDEEMED entitlements.
    Guarantees strict tenant isolation and customer-safe localized error messages.
    """
    if not hotspot.is_active:
        return {
            "success": False,
            "error_code": "INACTIVE_HOTSPOT",
            "message": get_customer_error_message("INACTIVE_HOTSPOT", lang)
        }

    from apps.vouchers.selectors.voucher_selectors import normalize_voucher_code

    company = hotspot.company
    code_clean = voucher_code.strip().upper()
    code_canonical = normalize_voucher_code(voucher_code)

    if not code_clean:
        return {
            "success": False,
            "error_code": "INVALID_CODE",
            "message": get_customer_error_message("INVALID_CODE", lang)
        }

    # Strict tenant-scoped voucher query with canonical code normalization
    voucher = Voucher.objects.select_related('plan', 'entitlement').filter(
        company=company,
    ).filter(
        models.Q(display_code__iexact=code_clean) | models.Q(display_code__iexact=code_canonical)
    ).first()

    if not voucher:
        return {
            "success": False,
            "error_code": "NOT_FOUND",
            "message": get_customer_error_message("NOT_FOUND", lang)
        }

    entitlement: Optional[AccessEntitlement] = None

    if voucher.status in (VoucherStatus.AVAILABLE, VoucherStatus.RESERVED):
        # Atomic first-time redemption
        try:
            _, entitlement = redeem_voucher(
                voucher_code=voucher.display_code,
                company=company,
                customer_phone=customer_phone
            )
        except ValidationError as e:
            logger.warning("Voucher redemption validation error for %s: %s", code_clean, e)
            return {
                "success": False,
                "error_code": "INVALID_CODE",
                "message": get_customer_error_message("INVALID_CODE", lang)
            }
        except Exception as e:
            logger.error("Unexpected error redeeming voucher %s: %s", code_clean, e)
            return {
                "success": False,
                "error_code": "GENERIC_ERROR",
                "message": get_customer_error_message("GENERIC_ERROR", lang)
            }

    elif voucher.status == VoucherStatus.REDEEMED:
        if hasattr(voucher, 'entitlement') and voucher.entitlement:
            entitlement = voucher.entitlement
        else:
            return {
                "success": False,
                "error_code": "EXPIRED",
                "message": get_customer_error_message("EXPIRED", lang)
            }

    elif voucher.status == VoucherStatus.REVOKED:
        return {
            "success": False,
            "error_code": "REVOKED",
            "message": get_customer_error_message("REVOKED", lang)
        }
    elif voucher.status == VoucherStatus.EXPIRED:
        return {
            "success": False,
            "error_code": "EXPIRED",
            "message": get_customer_error_message("EXPIRED", lang)
        }
    else:
        return {
            "success": False,
            "error_code": "INVALID_CODE",
            "message": get_customer_error_message("INVALID_CODE", lang)
        }

    # Verify authorizability on resolved entitlement
    if not entitlement:
        return {
            "success": False,
            "error_code": "NOT_FOUND",
            "message": get_customer_error_message("NOT_FOUND", lang)
        }

    authorizable, reason = is_entitlement_authorizable(entitlement)
    if not authorizable:
        error_code = reason or 'GENERIC_ERROR'
        return {
            "success": False,
            "error_code": error_code,
            "message": get_customer_error_message(error_code, lang)
        }

    # Calculate remaining time and data quota
    now = timezone.now()
    remaining_seconds: Optional[int] = None
    if entitlement.expires_at:
        remaining_seconds = max(0, int((entitlement.expires_at - now).total_seconds()))

    remaining_data_bytes: Optional[int] = None
    if entitlement.data_limit_bytes:
        remaining_data_bytes = max(0, entitlement.data_limit_bytes - entitlement.data_used_bytes)

    target_login_url = get_hotspot_login_url(hotspot, runtime_context)
    logger.info("PORTAL_HANDOFF_ATTEMPTED: voucher=%s hotspot=%s login_url=%s", voucher.display_code, hotspot.slug, target_login_url)

    return {
        "success": True,
        "username": voucher.display_code,
        "password": voucher.display_code,
        "entitlement_reference": entitlement.reference,
        "plan_name": entitlement.plan.name if entitlement.plan else "High-Speed Access",
        "download_speed_kbps": entitlement.download_speed_kbps,
        "upload_speed_kbps": entitlement.upload_speed_kbps,
        "remaining_seconds": remaining_seconds,
        "remaining_data_bytes": remaining_data_bytes,
        "router_login_url": target_login_url,
        "gateway_ip": hotspot.gateway_ip or "",
    }
