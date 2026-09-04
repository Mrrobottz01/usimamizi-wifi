import logging
from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.companies.models import Company, HotspotConfiguration
from apps.entitlements.models import AccessEntitlement
from apps.entitlements.services.entitlement_services import is_entitlement_authorizable
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
    """Resolve an active HotspotConfiguration by its public slug."""
    return HotspotConfiguration.objects.select_related('company').filter(
        slug__iexact=slug.strip()
    ).first()


def get_or_create_default_hotspot(company: Company) -> HotspotConfiguration:
    """Get or seed a default HotspotConfiguration for a company."""
    hotspot = HotspotConfiguration.objects.filter(company=company).first()
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
            is_active=True
        )
    return hotspot


def validate_and_redeem_portal_voucher(
    *,
    hotspot: HotspotConfiguration,
    voucher_code: str,
    customer_phone: Optional[str] = None,
    lang: str = 'EN'
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
        "router_login_url": hotspot.router_login_url,
    }
