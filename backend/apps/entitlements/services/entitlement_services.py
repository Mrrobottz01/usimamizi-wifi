import calendar
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.plans.models import DurationUnit, Plan, ValidityMode
from apps.vouchers.models import Voucher

from ..exceptions import (
    InvalidEntitlementStateTransition,
)
from ..models import (
    AccessEntitlement,
    EntitlementSourceType,
    EntitlementStatus,
)

logger = logging.getLogger(__name__)


def generate_entitlement_reference(company: Optional[Company] = None) -> str:
    """
    Generate concurrency-safe human-readable entitlement reference: ENT-YYYYMMDD-XXXXXX.
    """
    date_str = timezone.now().strftime('%Y%m%d')
    random_suffix = secrets.token_hex(3).upper()
    return f"ENT-{date_str}-{random_suffix}"


def create_plan_snapshot(plan: Plan) -> Dict[str, Any]:
    """
    Create an immutable frozen dictionary snapshot of commercial and rate-shaping plan properties.
    """
    return {
        "plan_id": str(plan.id),
        "plan_name": plan.name,
        "plan_code": plan.code,
        "duration_value": plan.duration_value,
        "duration_unit": plan.duration_unit,
        "validity_mode": plan.validity_mode,
        "download_speed_kbps": plan.download_speed_kbps,
        "upload_speed_kbps": plan.upload_speed_kbps,
        "data_limit_bytes": plan.data_limit_bytes,
        "max_devices": getattr(plan, 'max_devices', 1) or 1,
        "simultaneous_sessions": getattr(plan, 'simultaneous_sessions', 1) or 1,
        "idle_timeout_seconds": getattr(plan, 'idle_timeout_seconds', None),
        "session_timeout_seconds": getattr(plan, 'session_timeout_seconds', None),
        "price": str(plan.price),
        "currency": plan.currency,
        "snapshot_created_at": timezone.now().isoformat(),
    }


def add_months_to_date(source_date: datetime, months: int) -> datetime:
    """
    Add calendar months safely, capping at the target month's maximum days (e.g. Jan 31 + 1 mo -> Feb 28/29).
    """
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return source_date.replace(year=year, month=month, day=day)


def calculate_entitlement_validity(
    plan: Plan,
    start_time: datetime
) -> Tuple[datetime, Optional[datetime], Optional[int]]:
    """
    Calculate (valid_from, expires_at, usage_time_limit_seconds) based on plan validity mode and duration units.
    """
    valid_from = start_time
    duration_val = plan.duration_value
    unit = plan.duration_unit
    mode = plan.validity_mode

    if mode == ValidityMode.USAGE_TIME:
        # Duration specifies total accumulative active connection time
        seconds_map = {
            DurationUnit.MINUTES: duration_val * 60,
            DurationUnit.HOURS: duration_val * 3600,
            DurationUnit.DAYS: duration_val * 86400,
            DurationUnit.WEEKS: duration_val * 7 * 86400,
            DurationUnit.MONTHS: duration_val * 30 * 86400,
        }
        usage_time_limit_seconds = seconds_map.get(unit, duration_val * 3600)
        # Upper wall-clock expiration (e.g. 1 year max validity for unconsumed usage time)
        expires_at = start_time + timedelta(days=365)
        return (valid_from, expires_at, usage_time_limit_seconds)

    elif mode == ValidityMode.CALENDAR:
        if unit == DurationUnit.DAYS:
            # End of day arithmetic
            end_date = (start_time + timedelta(days=duration_val)).replace(hour=23, minute=59, second=59, microsecond=999999)
            return (valid_from, end_date, None)
        elif unit == DurationUnit.MONTHS:
            end_date = add_months_to_date(start_time, duration_val)
            return (valid_from, end_date, None)
        else:
            expires_at = start_time + timedelta(days=duration_val)
            return (valid_from, expires_at, None)

    else:
        # CONTINUOUS (Default) — Clock runs continuously from activation
        if unit == DurationUnit.MINUTES:
            delta = timedelta(minutes=duration_val)
        elif unit == DurationUnit.HOURS:
            delta = timedelta(hours=duration_val)
        elif unit == DurationUnit.DAYS:
            delta = timedelta(days=duration_val)
        elif unit == DurationUnit.WEEKS:
            delta = timedelta(weeks=duration_val)
        elif unit == DurationUnit.MONTHS:
            expires_at = add_months_to_date(start_time, duration_val)
            return (valid_from, expires_at, None)
        else:
            delta = timedelta(hours=duration_val)

        expires_at = start_time + delta
        return (valid_from, expires_at, None)


@transaction.atomic
def create_entitlement_from_plan(
    *,
    company: Company,
    plan: Plan,
    source_type: str,
    voucher: Optional[Voucher] = None,
    customer: Optional[Any] = None,
    created_by: Optional[Any] = None,
    activate_immediately: bool = True
) -> AccessEntitlement:
    """
    Core factory creating an AccessEntitlement with an immutable plan snapshot.
    """
    snapshot = create_plan_snapshot(plan)
    reference = generate_entitlement_reference(company)

    valid_from = None
    expires_at = None
    usage_time_limit_seconds = None
    activated_at = None
    status = EntitlementStatus.PENDING

    if activate_immediately:
        now = timezone.now()
        activated_at = now
        status = EntitlementStatus.ACTIVE
        valid_from, expires_at, usage_time_limit_seconds = calculate_entitlement_validity(plan, now)

    entitlement = AccessEntitlement.objects.create(
        company=company,
        customer=customer,
        voucher=voucher,
        plan=plan,
        source_type=source_type,
        status=status,
        reference=reference,
        activated_at=activated_at,
        valid_from=valid_from,
        expires_at=expires_at,
        validity_mode=plan.validity_mode,
        download_speed_kbps=plan.download_speed_kbps,
        upload_speed_kbps=plan.upload_speed_kbps,
        data_limit_bytes=plan.data_limit_bytes,
        usage_time_limit_seconds=usage_time_limit_seconds,
        max_devices=getattr(plan, 'max_devices', 1) or 1,
        simultaneous_sessions=getattr(plan, 'simultaneous_sessions', 1) or 1,
        idle_timeout_seconds=getattr(plan, 'idle_timeout_seconds', None),
        session_timeout_seconds=getattr(plan, 'session_timeout_seconds', None),
        plan_snapshot=snapshot,
        created_by=created_by
    )

    return entitlement


@transaction.atomic
def activate_entitlement(*, entitlement: AccessEntitlement) -> AccessEntitlement:
    """
    Transition entitlement from PENDING to ACTIVE and compute validity bounds.
    """
    if entitlement.status != EntitlementStatus.PENDING:
        raise InvalidEntitlementStateTransition(
            f"Cannot activate entitlement in status '{entitlement.status}'. Only PENDING entitlements can be activated."
        )

    now = timezone.now()
    valid_from, expires_at, usage_time_limit = calculate_entitlement_validity(entitlement.plan, now)

    entitlement.status = EntitlementStatus.ACTIVE
    entitlement.activated_at = now
    entitlement.valid_from = valid_from
    entitlement.expires_at = expires_at
    if usage_time_limit is not None:
        entitlement.usage_time_limit_seconds = usage_time_limit

    entitlement.save()
    return entitlement


@transaction.atomic
def suspend_entitlement(
    *,
    entitlement: AccessEntitlement,
    actor: Optional[Any] = None,
    reason: str = ''
) -> AccessEntitlement:
    """
    Suspend an ACTIVE entitlement.
    Policy: Continuous/Calendar expiry clock continues while access is blocked.
    """
    if entitlement.status != EntitlementStatus.ACTIVE:
        raise InvalidEntitlementStateTransition(
            f"Cannot suspend entitlement in status '{entitlement.status}'. Only ACTIVE entitlements can be suspended."
        )

    entitlement.status = EntitlementStatus.SUSPENDED
    entitlement.suspended_at = timezone.now()
    entitlement.suspended_by = actor
    entitlement.suspension_reason = reason
    entitlement.save()

    # Real-time session disconnect for active sessions
    try:
        from apps.hotspot_sessions.models import SessionDisconnectTrigger
        from apps.hotspot_sessions.services.session_control import (
            disconnect_active_sessions_for_entitlement,
        )
        disconnect_active_sessions_for_entitlement(
            entitlement=entitlement,
            trigger_type=SessionDisconnectTrigger.ENTITLEMENT_SUSPENDED,
            reason=reason or "Entitlement suspended by operator",
            requested_by=actor
        )
    except Exception as e:
        logger.warning("Failed to dispatch real-time disconnect on suspension for %s: %s", entitlement.id, e)

    return entitlement


@transaction.atomic
def resume_entitlement(
    *,
    entitlement: AccessEntitlement,
    actor: Optional[Any] = None
) -> AccessEntitlement:
    """
    Resume a SUSPENDED entitlement back to ACTIVE.
    """
    if entitlement.status != EntitlementStatus.SUSPENDED:
        raise InvalidEntitlementStateTransition(
            f"Cannot resume entitlement in status '{entitlement.status}'. Only SUSPENDED entitlements can be resumed."
        )

    entitlement.status = EntitlementStatus.ACTIVE
    entitlement.suspended_at = None
    entitlement.suspended_by = None
    entitlement.save()
    return entitlement


@transaction.atomic
def revoke_entitlement(
    *,
    entitlement: AccessEntitlement,
    actor: Optional[Any] = None,
    reason: str = ''
) -> AccessEntitlement:
    """
    Permanently revoke an entitlement.
    Allowed from: PENDING, ACTIVE, SUSPENDED.
    """
    if entitlement.status not in [EntitlementStatus.PENDING, EntitlementStatus.ACTIVE, EntitlementStatus.SUSPENDED]:
        raise InvalidEntitlementStateTransition(
            f"Cannot revoke entitlement in terminal status '{entitlement.status}'."
        )

    if not reason:
        raise ValidationError({"reason": "Revocation reason is required."})

    entitlement.status = EntitlementStatus.REVOKED
    entitlement.revoked_at = timezone.now()
    entitlement.revoked_by = actor
    entitlement.revocation_reason = reason
    entitlement.save()

    # Real-time session disconnect for active sessions
    try:
        from apps.hotspot_sessions.models import SessionDisconnectTrigger
        from apps.hotspot_sessions.services.session_control import (
            disconnect_active_sessions_for_entitlement,
        )
        disconnect_active_sessions_for_entitlement(
            entitlement=entitlement,
            trigger_type=SessionDisconnectTrigger.ENTITLEMENT_REVOKED,
            reason=reason or "Entitlement revoked by operator",
            requested_by=actor
        )
    except Exception as e:
        logger.warning("Failed to dispatch real-time disconnect on revocation for %s: %s", entitlement.id, e)

    return entitlement


@transaction.atomic
def expire_entitlement(*, entitlement: AccessEntitlement) -> AccessEntitlement:
    """
    Mark an entitlement as EXPIRED.
    """
    if entitlement.status == EntitlementStatus.EXPIRED:
        return entitlement

    if entitlement.status == EntitlementStatus.REVOKED:
        raise InvalidEntitlementStateTransition("Cannot expire a REVOKED entitlement.")

    entitlement.status = EntitlementStatus.EXPIRED
    entitlement.save()
    return entitlement


@transaction.atomic
def grant_manual_entitlement(
    *,
    company: Company,
    plan: Plan,
    actor: Any,
    reason: str,
    customer: Optional[Any] = None
) -> AccessEntitlement:
    """
    Grant access manually with mandatory reason and audit metadata.
    """
    if plan.company != company:
        raise ValidationError({"plan": "Plan does not belong to the specified company."})

    if not reason or not reason.strip():
        raise ValidationError({"reason": "A valid reason is required for manual access grants."})

    entitlement = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        customer=customer,
        created_by=actor,
        activate_immediately=True
    )
    return entitlement


def is_entitlement_authorizable(entitlement: AccessEntitlement) -> Tuple[bool, str]:
    """
    Evaluate whether the entitlement is valid for network authorization.
    Consumed by FreeRADIUS and AAA controllers in Phase 4.
    """
    if not entitlement:
        return (False, "ENTITLEMENT_NOT_FOUND")

    if entitlement.status == EntitlementStatus.REVOKED:
        return (False, "REVOKED")

    if entitlement.status == EntitlementStatus.SUSPENDED:
        return (False, "SUSPENDED")

    if entitlement.status == EntitlementStatus.EXPIRED:
        return (False, "EXPIRED")

    if entitlement.status != EntitlementStatus.ACTIVE:
        return (False, "NOT_ACTIVE")

    now = timezone.now()

    # Time Bounds
    if entitlement.valid_from and entitlement.valid_from > now:
        return (False, "NOT_YET_VALID")

    if entitlement.expires_at and entitlement.expires_at <= now:
        return (False, "EXPIRED")

    # Data Quota
    if entitlement.data_limit_bytes is not None and entitlement.data_used_bytes >= entitlement.data_limit_bytes:
        return (False, "DATA_QUOTA_EXHAUSTED")

    # Usage Time Quota (applies when positive usage_time_limit_seconds is configured)
    if (
        entitlement.usage_time_limit_seconds is not None
        and entitlement.usage_time_limit_seconds > 0
        and entitlement.usage_time_used_seconds >= entitlement.usage_time_limit_seconds
    ):
        return (False, "USAGE_TIME_EXHAUSTED")

    return (True, "AUTHORIZED")
