import re
from typing import Any, Dict, Optional

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.entitlements.models import AccessEntitlement
from apps.entitlements.services.entitlement_services import is_entitlement_authorizable
from apps.hotspot_sessions.services.session_services import (
    get_active_sessions_count_for_entitlement,
    get_or_create_active_session,
    terminate_session,
    update_session_accounting,
)
from apps.vouchers.models import Voucher, VoucherStatus
from apps.vouchers.services.voucher_services import redeem_voucher

from ..models import (
    AccountingPacketType,
    EntitlementDevice,
    RadiusAccountingLog,
    RadiusClient,
)


def normalize_mac_address(raw_mac: Optional[str]) -> str:
    """
    Normalize MAC address string to canonical uppercase colon-separated format (AA:BB:CC:DD:EE:FF).
    """
    if not raw_mac:
        return ""
    clean = re.sub(r'[^A-Fa-f0-9]', '', raw_mac.strip().upper())
    if len(clean) == 12:
        return ':'.join(clean[i:i+2] for i in range(0, 12, 2))
    return raw_mac.strip().upper()


def resolve_nas(nas_ip: Optional[str] = None, nas_identifier: Optional[str] = None) -> Optional[RadiusClient]:
    """
    Resolve authorized NAS router client.
    Supports direct nas_ip, router management_ip, router gateway_ip, server IP, and loopback fallback.
    """
    if nas_ip and nas_ip not in ['127.0.0.1', 'localhost']:
        client = RadiusClient.objects.filter(nas_ip=nas_ip).first()
        if client:
            return client
        client = RadiusClient.objects.filter(router__management_ip=nas_ip).first()
        if client:
            return client
        client = RadiusClient.objects.filter(router__hotspots__gateway_ip=nas_ip).first()
        if client:
            return client
        if nas_ip == '23.95.130.161':
            return RadiusClient.objects.filter(is_active=True).first()
        if nas_identifier:
            client = RadiusClient.objects.filter(nas_identifier=nas_identifier).first()
            if client:
                return client
        return None

    if nas_identifier:
        client = RadiusClient.objects.filter(nas_identifier=nas_identifier).first()
        if client:
            return client

    # Local development / Localhost fallback
    return RadiusClient.objects.filter(is_active=True).first()


def calculate_session_timeout(entitlement: AccessEntitlement) -> int:
    """
    Calculate dynamic Session-Timeout in seconds.
    Bounds session duration to the minimum of configured plan session timeout,
    remaining continuous validity time, and remaining usage time quota.
    """
    timeouts = []

    # 1. Configured plan session timeout
    if entitlement.session_timeout_seconds:
        timeouts.append(entitlement.session_timeout_seconds)

    now = timezone.now()

    # 2. Continuous / Calendar expiration bound
    if entitlement.expires_at:
        remaining_seconds = int((entitlement.expires_at - now).total_seconds())
        timeouts.append(max(0, remaining_seconds))

    # 3. Usage-Time quota bound
    if entitlement.usage_time_limit_seconds is not None and entitlement.usage_time_limit_seconds > 0:
        usage_remaining = max(0, entitlement.usage_time_limit_seconds - entitlement.usage_time_used_seconds)
        timeouts.append(usage_remaining)

    if not timeouts:
        return 3600  # Default 1 hour fallback

    effective_timeout = min(timeouts)
    return effective_timeout


def generate_mikrotik_rate_limit(download_speed_kbps: Optional[int], upload_speed_kbps: Optional[int]) -> str:
    """
    Generate MikroTik-Rate-Limit VSA string: rx-rate/tx-rate (Upload/Download in kbps).
    RouterOS convention: Rx = client upload to router, Tx = client download from router.
    """
    if not download_speed_kbps and not upload_speed_kbps:
        return ""
    up = f"{upload_speed_kbps}k" if upload_speed_kbps else "0k"
    down = f"{download_speed_kbps}k" if download_speed_kbps else "0k"
    return f"{up}/{down}"


@transaction.atomic
def authorize_radius_access(
    *,
    username: str,
    password: Optional[str] = None,
    nas_ip: Optional[str] = None,
    nas_identifier: Optional[str] = None,
    mac_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Authoritative centralized AAA authorization service.
    Evaluates NAS validity, tenant context, AccessEntitlement state, device limits,
    simultaneous sessions, and dynamically computes rate shaping & session timeouts.
    """
    username_clean = username.strip()
    norm_mac = normalize_mac_address(mac_address)

    # 1. NAS Identification & Security Gate
    nas = resolve_nas(nas_ip=nas_ip, nas_identifier=nas_identifier)
    if not nas:
        return {
            "accept": False,
            "code": "Access-Reject",
            "reason": "UNKNOWN_NAS",
            "reply": {"Reply-Message": "NAS router is unauthorized or unknown."}
        }

    if not nas.is_active:
        return {
            "accept": False,
            "code": "Access-Reject",
            "reason": "NAS_DISABLED",
            "reply": {"Reply-Message": "NAS router is disabled."}
        }

    company = nas.company

    # 2. AccessEntitlement Resolution (Tenant-Scoped)
    entitlement: Optional[AccessEntitlement] = None

    from apps.vouchers.selectors.voucher_selectors import normalize_voucher_code
    canonical_username = normalize_voucher_code(username_clean)

    # Try Voucher lookup
    voucher = Voucher.objects.select_related('entitlement', 'plan').filter(
        company=company
    ).filter(
        models.Q(display_code__iexact=username_clean) | models.Q(display_code__iexact=canonical_username)
    ).first()

    if not voucher:
        voucher = Voucher.objects.select_related('entitlement', 'plan').filter(
            models.Q(display_code__iexact=username_clean) | models.Q(display_code__iexact=canonical_username)
        ).first()

    if voucher:
        if hasattr(voucher, 'entitlement') and voucher.entitlement:
            entitlement = voucher.entitlement
            if entitlement.status == 'PENDING':
                entitlement.status = 'ACTIVE'
                entitlement.activated_at = timezone.now()
                entitlement.save(update_fields=['status', 'activated_at', 'updated_at'])
        elif voucher.status in (VoucherStatus.AVAILABLE, VoucherStatus.RESERVED):
            try:
                _, entitlement = redeem_voucher(
                    voucher_code=voucher.display_code,
                    company=voucher.company
                )
            except Exception:
                pass

    # Try Entitlement reference lookup
    if not entitlement:
        entitlement = AccessEntitlement.objects.select_related('plan').filter(
            company=company,
            reference__iexact=username_clean
        ).first()

    # Try User account lookup
    if not entitlement:
        user = User.objects.filter(email__iexact=username_clean).first()
        if user:
            if password and not user.check_password(password):
                return {
                    "accept": False,
                    "code": "Access-Reject",
                    "reason": "INVALID_CREDENTIAL",
                    "reply": {"Reply-Message": "Invalid password."}
                }
            entitlement = AccessEntitlement.objects.select_related('plan').filter(
                company=company,
                customer=user,
                status='ACTIVE'
            ).first()

    if not entitlement:
        return {
            "accept": False,
            "code": "Access-Reject",
            "reason": "ENTITLEMENT_NOT_FOUND",
            "reply": {"Reply-Message": "No active access entitlement found."}
        }

    # 3. AccessEntitlement Authorization Check
    is_valid, denial_reason = is_entitlement_authorizable(entitlement)
    if not is_valid:
        return {
            "accept": False,
            "code": "Access-Reject",
            "reason": denial_reason,
            "reply": {"Reply-Message": f"Access denied: {denial_reason}."}
        }

    # 4. Device Limit Policy (max_devices)
    if norm_mac:
        device_bound = EntitlementDevice.objects.filter(
            entitlement=entitlement,
            mac_address=norm_mac
        ).exists()

        if not device_bound:
            current_device_count = EntitlementDevice.objects.filter(entitlement=entitlement).count()
            if current_device_count >= entitlement.max_devices:
                return {
                    "accept": False,
                    "code": "Access-Reject",
                    "reason": "DEVICE_LIMIT_REACHED",
                    "reply": {"Reply-Message": f"Maximum allowed devices ({entitlement.max_devices}) reached for this access pass."}
                }
            # Bind device to entitlement
            EntitlementDevice.objects.create(
                entitlement=entitlement,
                mac_address=norm_mac
            )

    # 5. Simultaneous Sessions Policy (simultaneous_sessions)
    active_sessions = get_active_sessions_count_for_entitlement(entitlement)
    if active_sessions >= entitlement.simultaneous_sessions:
        return {
            "accept": False,
            "code": "Access-Reject",
            "reason": "SESSION_LIMIT_REACHED",
            "reply": {"Reply-Message": f"Simultaneous session limit ({entitlement.simultaneous_sessions}) reached."}
        }

    # 6. Dynamic Session-Timeout Calculation
    session_timeout = calculate_session_timeout(entitlement)
    if session_timeout <= 0:
        return {
            "accept": False,
            "code": "Access-Reject",
            "reason": "EXPIRED",
            "reply": {"Reply-Message": "Entitlement has expired."}
        }

    # 7. Construct Access-Accept Reply Attributes
    reply_attributes: Dict[str, Any] = {
        "Session-Timeout": session_timeout,
        "Idle-Timeout": entitlement.idle_timeout_seconds or 300,
        "Acct-Interim-Interval": getattr(settings, 'RADIUS_ACCT_INTERIM_INTERVAL', 60),
    }

    # Dynamic Bandwidth Rate Limiting
    rate_limit_str = generate_mikrotik_rate_limit(
        download_speed_kbps=entitlement.download_speed_kbps,
        upload_speed_kbps=entitlement.upload_speed_kbps
    )
    if rate_limit_str:
        reply_attributes["Mikrotik-Rate-Limit"] = rate_limit_str

    if entitlement.download_speed_kbps:
        reply_attributes["WISPr-Bandwidth-Max-Down"] = entitlement.download_speed_kbps * 1000
    if entitlement.upload_speed_kbps:
        reply_attributes["WISPr-Bandwidth-Max-Up"] = entitlement.upload_speed_kbps * 1000

    return {
        "accept": True,
        "code": "Access-Accept",
        "reason": "AUTHORIZED",
        "entitlement_id": str(entitlement.id),
        "entitlement_reference": entitlement.reference,
        "reply": reply_attributes,
    }


@transaction.atomic
def process_radius_accounting(
    *,
    session_id: str,
    username: str,
    nas_ip: str,
    packet_type: str,
    nas_identifier: Optional[str] = None,
    mac_address: str = "",
    framed_ip: Optional[str] = None,
    input_octets: int = 0,
    output_octets: int = 0,
    input_gigawords: int = 0,
    output_gigawords: int = 0,
    session_time: int = 0,
    terminate_cause: str = "",
    raw_payload: Optional[Dict[str, Any]] = None
) -> RadiusAccountingLog:
    """
    Process incoming RADIUS accounting packet atomically and idempotently.
    Updates HotspotSession and applies cumulative positive usage deltas to AccessEntitlement.
    """
    norm_mac = normalize_mac_address(mac_address)
    nas = resolve_nas(nas_ip=nas_ip, nas_identifier=nas_identifier)
    company = nas.company if nas else None

    # Calculate 64-bit byte counters safely from octets and gigawords
    total_in = (input_gigawords * (2**32)) + int(input_octets or 0)
    total_out = (output_gigawords * (2**32)) + int(output_octets or 0)
    total_bytes = total_in + total_out

    # Resolve AccessEntitlement
    entitlement: Optional[AccessEntitlement] = None
    if company:
        from apps.vouchers.selectors.voucher_selectors import normalize_voucher_code
        canonical_username = normalize_voucher_code(username)

        # Check Voucher
        voucher = Voucher.objects.select_related('entitlement').filter(
            company=company
        ).filter(
            models.Q(display_code__iexact=username) | models.Q(display_code__iexact=canonical_username)
        ).first()
        if voucher:
            if hasattr(voucher, 'entitlement') and voucher.entitlement:
                entitlement = voucher.entitlement
            elif voucher.status in (VoucherStatus.AVAILABLE, VoucherStatus.RESERVED):
                try:
                    _, entitlement = redeem_voucher(voucher_code=voucher.display_code, company=company)
                except Exception:
                    pass

        # Check Entitlement reference
        if not entitlement:
            entitlement = AccessEntitlement.objects.filter(
                company=company,
                reference__iexact=username
            ).first()

    # HotspotSession State & Delta Calculation
    if company and entitlement:
        if packet_type == AccountingPacketType.START:
            get_or_create_active_session(
                company=company,
                entitlement=entitlement,
                radius_client=nas,
                acct_session_id=session_id,
                username=username,
                mac_address=norm_mac,
                ip_address=framed_ip
            )

        elif packet_type == AccountingPacketType.INTERIM:
            session = get_or_create_active_session(
                company=company,
                entitlement=entitlement,
                radius_client=nas,
                acct_session_id=session_id,
                username=username,
                mac_address=norm_mac,
                ip_address=framed_ip
            )
            # Positive cumulative deltas
            prev_bytes = session.input_bytes + session.output_bytes
            delta_bytes = max(0, total_bytes - prev_bytes)
            delta_seconds = max(0, int(session_time or 0) - session.session_seconds)

            update_session_accounting(
                session=session,
                input_bytes=total_in,
                output_bytes=total_out,
                session_seconds=int(session_time or 0),
                ip_address=framed_ip
            )

            # Apply delta to AccessEntitlement atomically
            if delta_bytes > 0:
                entitlement.data_used_bytes += delta_bytes
            if delta_seconds > 0:
                entitlement.usage_time_used_seconds += delta_seconds
            if delta_bytes > 0 or delta_seconds > 0:
                entitlement.save(update_fields=['data_used_bytes', 'usage_time_used_seconds', 'updated_at'])

            # Real-time disconnect trigger on quota exhaustion
            if entitlement.data_limit_bytes and entitlement.data_used_bytes >= entitlement.data_limit_bytes:
                try:
                    from apps.hotspot_sessions.models import SessionDisconnectTrigger
                    from apps.hotspot_sessions.services.session_control import (
                        disconnect_hotspot_session,
                    )
                    disconnect_hotspot_session(
                        session=session,
                        trigger_type=SessionDisconnectTrigger.DATA_QUOTA_EXHAUSTED,
                        reason="Data quota exhausted"
                    )
                except Exception:
                    pass
            elif entitlement.usage_time_limit_seconds and entitlement.usage_time_used_seconds >= entitlement.usage_time_limit_seconds:
                try:
                    from apps.hotspot_sessions.models import SessionDisconnectTrigger
                    from apps.hotspot_sessions.services.session_control import (
                        disconnect_hotspot_session,
                    )
                    disconnect_hotspot_session(
                        session=session,
                        trigger_type=SessionDisconnectTrigger.USAGE_TIME_EXHAUSTED,
                        reason="Usage time exhausted"
                    )
                except Exception:
                    pass

        elif packet_type == AccountingPacketType.STOP:
            session = get_or_create_active_session(
                company=company,
                entitlement=entitlement,
                radius_client=nas,
                acct_session_id=session_id,
                username=username,
                mac_address=norm_mac,
                ip_address=framed_ip
            )
            prev_bytes = session.input_bytes + session.output_bytes
            delta_bytes = max(0, total_bytes - prev_bytes)
            delta_seconds = max(0, int(session_time or 0) - session.session_seconds)

            terminate_session(
                session=session,
                input_bytes=total_in,
                output_bytes=total_out,
                session_seconds=int(session_time or 0),
                termination_reason=terminate_cause
            )

            if delta_bytes > 0:
                entitlement.data_used_bytes += delta_bytes
            if delta_seconds > 0:
                entitlement.usage_time_used_seconds += delta_seconds
            if delta_bytes > 0 or delta_seconds > 0:
                entitlement.save(update_fields=['data_used_bytes', 'usage_time_used_seconds', 'updated_at'])

    # Immutable Log Entry
    log_entry = RadiusAccountingLog.objects.create(
        company=company,
        radius_client=nas,
        entitlement=entitlement,
        session_id=session_id,
        username=username,
        nas_ip=nas_ip,
        nas_identifier=nas_identifier or '',
        mac_address=norm_mac,
        framed_ip=framed_ip,
        packet_type=packet_type,
        input_octets=int(input_octets or 0),
        output_octets=int(output_octets or 0),
        input_gigawords=int(input_gigawords or 0),
        output_gigawords=int(output_gigawords or 0),
        total_input_bytes=total_in,
        total_output_bytes=total_out,
        session_time=int(session_time or 0),
        terminate_cause=terminate_cause,
        raw_payload=raw_payload or {}
    )

    return log_entry
