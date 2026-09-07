import logging
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from django.db import models, transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.companies.models import HotspotConfiguration
from apps.entitlements.models import (
    AccessEntitlement,
    EntitlementSourceType,
    EntitlementStatus,
)
from apps.entitlements.services.entitlement_services import (
    calculate_entitlement_validity,
    create_plan_snapshot,
    revoke_entitlement,
)
from apps.hotspot_sessions.models import HotspotSession, SessionStatus, SessionDisconnectTrigger
from apps.hotspot_sessions.services.session_control import disconnect_hotspot_session
from apps.notifications.models import NotificationMessage, NotificationStatus
from apps.notifications.services.sms_services import route_and_send_sms
from apps.plans.models import DurationUnit, Plan
from ..models import (
    Customer,
    CustomerSubscriptionSettings,
    Subscription,
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionRenewalMode,
    SubscriptionSource,
    SubscriptionStatus,
)

logger = logging.getLogger(__name__)


def calculate_plan_duration(plan: Plan) -> timedelta:
    """Calculate timedelta for plan duration."""
    val = plan.duration_value
    unit = plan.duration_unit
    if unit == DurationUnit.MINUTES:
        return timedelta(minutes=val)
    elif unit == DurationUnit.HOURS:
        return timedelta(hours=val)
    elif unit == DurationUnit.DAYS:
        return timedelta(days=val)
    elif unit == DurationUnit.WEEKS:
        return timedelta(weeks=val)
    elif unit == DurationUnit.MONTHS:
        return timedelta(days=val * 30)
    return timedelta(hours=1)


@transaction.atomic
def create_subscription(
    customer: Customer,
    plan: Plan,
    hotspot: Optional[HotspotConfiguration] = None,
    source: str = SubscriptionSource.SELF_SERVICE_PAYMENT,
    user=None,
    auto_activate: bool = True
) -> Subscription:
    """
    Establish a commercial subscription contract for a customer on a plan.
    """
    plan_snapshot = create_plan_snapshot(plan)
    subscription = Subscription.objects.create(
        company=customer.company,
        customer=customer,
        plan=plan,
        hotspot=hotspot,
        status=SubscriptionStatus.PENDING,
        renewal_mode=SubscriptionRenewalMode.MANUAL,
        source=source,
        plan_snapshot=plan_snapshot,
    )

    SubscriptionEvent.objects.create(
        subscription=subscription,
        event_type=SubscriptionEventType.CREATED,
        old_status='',
        new_status=SubscriptionStatus.PENDING,
        actor=user,
        source=source,
        metadata={'plan_name': plan.name, 'price': str(plan.price)},
    )

    if auto_activate:
        subscription, _ = activate_subscription(subscription, user=user)

    return subscription


@transaction.atomic
def activate_subscription(
    subscription: Subscription,
    user=None
) -> Tuple[Subscription, AccessEntitlement]:
    """
    Activate a pending or newly created subscription and issue initial AccessEntitlement.
    """
    now = timezone.now()
    duration = calculate_plan_duration(subscription.plan)
    period_end = now + duration

    subscription.status = SubscriptionStatus.ACTIVE
    subscription.started_at = now
    subscription.current_period_start = now
    subscription.current_period_end = period_end
    subscription.grace_period_end = None
    subscription.save(update_fields=[
        'status', 'started_at', 'current_period_start', 'current_period_end', 'grace_period_end', 'updated_at'
    ])

    # Issue concrete AccessEntitlement for FreeRADIUS
    date_str = now.strftime("%Y%m%d")
    ent_ref = f"SUB-{date_str}-{secrets.token_hex(3).upper()}"
    plan = subscription.plan

    entitlement = AccessEntitlement.objects.create(
        company=subscription.company,
        customer=None,
        consumer=subscription.customer,
        subscription=subscription,
        plan=plan,
        source_type=EntitlementSourceType.PAYMENT if subscription.source == SubscriptionSource.SELF_SERVICE_PAYMENT else EntitlementSourceType.MANUAL,
        status=EntitlementStatus.ACTIVE,
        reference=ent_ref,
        activated_at=now,
        valid_from=now,
        expires_at=period_end,
        validity_mode=plan.validity_mode,
        download_speed_kbps=plan.download_speed_kbps,
        upload_speed_kbps=plan.upload_speed_kbps,
        data_limit_bytes=plan.data_limit_bytes,
        max_devices=plan.max_devices,
        simultaneous_sessions=plan.simultaneous_sessions,
        idle_timeout_seconds=plan.idle_timeout_seconds,
        session_timeout_seconds=plan.session_timeout_seconds,
        plan_snapshot=subscription.plan_snapshot,
    )

    SubscriptionEvent.objects.create(
        subscription=subscription,
        event_type=SubscriptionEventType.ACTIVATED,
        old_status=SubscriptionStatus.PENDING,
        new_status=SubscriptionStatus.ACTIVE,
        actor=user,
        source='ACTIVATION',
        metadata={'entitlement_reference': entitlement.reference, 'expires_at': period_end.isoformat()},
    )

    AuditLog.objects.create(
        company=subscription.company,
        user=user,
        action='SUBSCRIPTION_ACTIVATED',
        resource_type='Subscription',
        resource_id=str(subscription.id),
        changes={'status': SubscriptionStatus.ACTIVE, 'entitlement': entitlement.reference}
    )

    return subscription, entitlement


@transaction.atomic
def renew_subscription(
    subscription: Subscription,
    payment=None,
    user=None
) -> Tuple[Subscription, AccessEntitlement]:
    """
    Renew a customer's subscription.
    Explicit Commercial Rule:
    - If Active: new period appends strictly AFTER current_period_end (Zero lost paid time).
    - If Expired or Grace: new period starts immediately from now.
    """
    now = timezone.now()
    duration = calculate_plan_duration(subscription.plan)
    old_status = subscription.status

    if subscription.status == SubscriptionStatus.ACTIVE and subscription.current_period_end and subscription.current_period_end > now:
        # Active extension: preserve all remaining time
        new_start = subscription.current_period_end
        new_end = subscription.current_period_end + duration
    else:
        # Expired or grace fresh start
        new_start = now
        new_end = now + duration

    subscription.status = SubscriptionStatus.ACTIVE
    subscription.current_period_start = new_start
    subscription.current_period_end = new_end
    subscription.grace_period_end = None
    subscription.save(update_fields=[
        'status', 'current_period_start', 'current_period_end', 'grace_period_end', 'updated_at'
    ])

    date_str = now.strftime("%Y%m%d")
    ent_ref = f"RNW-{date_str}-{secrets.token_hex(3).upper()}"
    plan = subscription.plan

    entitlement = AccessEntitlement.objects.create(
        company=subscription.company,
        customer=None,
        consumer=subscription.customer,
        subscription=subscription,
        plan=plan,
        source_type=EntitlementSourceType.PAYMENT,
        status=EntitlementStatus.ACTIVE,
        reference=ent_ref,
        activated_at=now,
        valid_from=new_start,
        expires_at=new_end,
        validity_mode=plan.validity_mode,
        download_speed_kbps=plan.download_speed_kbps,
        upload_speed_kbps=plan.upload_speed_kbps,
        data_limit_bytes=plan.data_limit_bytes,
        max_devices=plan.max_devices,
        simultaneous_sessions=plan.simultaneous_sessions,
        idle_timeout_seconds=plan.idle_timeout_seconds,
        session_timeout_seconds=plan.session_timeout_seconds,
        plan_snapshot=subscription.plan_snapshot,
    )

    SubscriptionEvent.objects.create(
        subscription=subscription,
        event_type=SubscriptionEventType.RENEWED,
        old_status=old_status,
        new_status=SubscriptionStatus.ACTIVE,
        actor=user,
        source='PAYMENT' if payment else 'MANUAL',
        metadata={
            'new_period_start': new_start.isoformat(),
            'new_period_end': new_end.isoformat(),
            'entitlement_reference': entitlement.reference,
            'payment_reference': payment.reference if payment else None,
        },
    )

    # Dispatch confirmation SMS
    try:
        brand = subscription.hotspot.brand_name if (subscription.hotspot and subscription.hotspot.brand_name) else subscription.company.name
        end_formatted = new_end.strftime("%d/%m/%Y %H:%M")
        sms_text = f"{brand}: Your Wi-Fi plan ({plan.name}) has been renewed. Valid until {end_formatted}. Enjoy high-speed access!"
        msg = NotificationMessage.objects.create(
            company=subscription.company,
            channel='SMS',
            recipient=subscription.customer.normalized_phone,
            phone_normalized=subscription.customer.normalized_phone,
            rendered_content=sms_text,
            status=NotificationStatus.QUEUED,
        )
        route_and_send_sms(notification_message=msg)
    except Exception as e:
        logger.warning("Failed to send renewal SMS confirmation: %s", e)

    AuditLog.objects.create(
        company=subscription.company,
        user=user,
        action='SUBSCRIPTION_RENEWED',
        resource_type='Subscription',
        resource_id=str(subscription.id),
        changes={
            'old_status': old_status,
            'new_status': SubscriptionStatus.ACTIVE,
            'valid_until': new_end.isoformat(),
            'entitlement': entitlement.reference
        }
    )

    return subscription, entitlement


@transaction.atomic
def suspend_subscription(
    subscription: Subscription,
    reason: str = '',
    user=None
) -> Subscription:
    """
    Suspend an active subscription. Revokes active entitlements and disconnects active physical sessions.
    """
    old_status = subscription.status
    now = timezone.now()

    subscription.status = SubscriptionStatus.SUSPENDED
    subscription.suspended_at = now
    subscription.save(update_fields=['status', 'suspended_at', 'updated_at'])

    # Revoke all active entitlements belonging to this subscription
    active_ents = subscription.entitlements.filter(status=EntitlementStatus.ACTIVE)
    for ent in active_ents:
        revoke_entitlement(
            entitlement=ent,
            actor=user,
            reason=f"Subscription suspended: {reason}" if reason else "Subscription suspended"
        )

    # Disconnect any live hotspot sessions
    active_sessions = HotspotSession.objects.filter(
        subscription=subscription,
        status=SessionStatus.ACTIVE
    )
    for s in active_sessions:
        try:
            disconnect_hotspot_session(
                session=s,
                trigger_type=SessionDisconnectTrigger.SUBSCRIPTION_EXPIRED,
                reason=f"Subscription suspended: {reason}" if reason else "Subscription suspended",
                requested_by=user
            )
        except Exception as e:
            logger.warning("Could not disconnect session %s during subscription suspension: %s", s.id, e)

    SubscriptionEvent.objects.create(
        subscription=subscription,
        event_type=SubscriptionEventType.SUSPENDED,
        old_status=old_status,
        new_status=SubscriptionStatus.SUSPENDED,
        actor=user,
        source='ADMIN',
        metadata={'reason': reason},
    )

    AuditLog.objects.create(
        company=subscription.company,
        user=user,
        action='SUBSCRIPTION_SUSPENDED',
        resource_type='Subscription',
        resource_id=str(subscription.id),
        changes={'old_status': old_status, 'new_status': SubscriptionStatus.SUSPENDED, 'reason': reason}
    )

    return subscription


@transaction.atomic
def reactivate_subscription(
    subscription: Subscription,
    user=None
) -> Tuple[Subscription, Optional[AccessEntitlement]]:
    """
    Reactivate a suspended subscription if its period is still valid.
    """
    now = timezone.now()
    if not subscription.current_period_end or subscription.current_period_end <= now:
        raise ValueError("Cannot reactivate an expired subscription. Please renew.")

    old_status = subscription.status
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.suspended_at = None
    subscription.save(update_fields=['status', 'suspended_at', 'updated_at'])

    # Re-issue active entitlement
    date_str = now.strftime("%Y%m%d")
    ent_ref = f"REC-{date_str}-{secrets.token_hex(3).upper()}"
    plan = subscription.plan

    entitlement = AccessEntitlement.objects.create(
        company=subscription.company,
        customer=None,
        consumer=subscription.customer,
        subscription=subscription,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        status=EntitlementStatus.ACTIVE,
        reference=ent_ref,
        activated_at=now,
        valid_from=now,
        expires_at=subscription.current_period_end,
        validity_mode=plan.validity_mode,
        download_speed_kbps=plan.download_speed_kbps,
        upload_speed_kbps=plan.upload_speed_kbps,
        data_limit_bytes=plan.data_limit_bytes,
        max_devices=plan.max_devices,
        simultaneous_sessions=plan.simultaneous_sessions,
        idle_timeout_seconds=plan.idle_timeout_seconds,
        session_timeout_seconds=plan.session_timeout_seconds,
        plan_snapshot=subscription.plan_snapshot,
    )

    SubscriptionEvent.objects.create(
        subscription=subscription,
        event_type=SubscriptionEventType.REACTIVATED,
        old_status=old_status,
        new_status=SubscriptionStatus.ACTIVE,
        actor=user,
        source='ADMIN',
        metadata={'entitlement_reference': entitlement.reference},
    )

    AuditLog.objects.create(
        company=subscription.company,
        user=user,
        action='SUBSCRIPTION_REACTIVATED',
        resource_type='Subscription',
        resource_id=str(subscription.id),
        changes={'old_status': old_status, 'new_status': SubscriptionStatus.ACTIVE}
    )

    return subscription, entitlement


def process_subscription_expiries() -> Dict[str, int]:
    """
    Periodic job to evaluate expired subscriptions, apply grace periods,
    and disconnect physical sessions.
    """
    now = timezone.now()
    stats = {'grace_entered': 0, 'expired': 0}

    # Step 1: Active subscriptions past current_period_end
    active_past_end = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        current_period_end__lte=now
    )

    for sub in active_past_end:
        settings_obj, _ = CustomerSubscriptionSettings.objects.get_or_create(company=sub.company)
        grace_mins = settings_obj.grace_period_minutes

        if grace_mins > 0:
            grace_end = sub.current_period_end + timedelta(minutes=grace_mins)
            if now < grace_end:
                # Enter Grace period
                sub.status = SubscriptionStatus.GRACE
                sub.grace_period_end = grace_end
                sub.save(update_fields=['status', 'grace_period_end', 'updated_at'])
                SubscriptionEvent.objects.create(
                    subscription=sub,
                    event_type=SubscriptionEventType.GRACE_ENTERED,
                    old_status=SubscriptionStatus.ACTIVE,
                    new_status=SubscriptionStatus.GRACE,
                    source='EXPIRY_JOB',
                    metadata={'grace_period_end': grace_end.isoformat()},
                )
                stats['grace_entered'] += 1
                continue

        # Expire immediately
        sub.status = SubscriptionStatus.EXPIRED
        sub.save(update_fields=['status', 'updated_at'])
        SubscriptionEvent.objects.create(
            subscription=sub,
            event_type=SubscriptionEventType.EXPIRED,
            old_status=SubscriptionStatus.ACTIVE,
            new_status=SubscriptionStatus.EXPIRED,
            source='EXPIRY_JOB',
        )
        stats['expired'] += 1

        # Revoke active entitlements and disconnect
        for ent in sub.entitlements.filter(status=EntitlementStatus.ACTIVE):
            revoke_entitlement(entitlement=ent, reason="Subscription expired")

        for s in HotspotSession.objects.filter(subscription=sub, status=SessionStatus.ACTIVE):
            try:
                disconnect_hotspot_session(
                    session=s,
                    trigger_type=SessionDisconnectTrigger.SUBSCRIPTION_EXPIRED,
                    reason="Subscription expired"
                )
            except Exception:
                pass

    # Step 2: Grace subscriptions past grace_period_end
    grace_past_end = Subscription.objects.filter(
        status=SubscriptionStatus.GRACE,
        grace_period_end__lte=now
    )

    for sub in grace_past_end:
        sub.status = SubscriptionStatus.EXPIRED
        sub.save(update_fields=['status', 'updated_at'])
        SubscriptionEvent.objects.create(
            subscription=sub,
            event_type=SubscriptionEventType.EXPIRED,
            old_status=SubscriptionStatus.GRACE,
            new_status=SubscriptionStatus.EXPIRED,
            source='EXPIRY_JOB',
        )
        stats['expired'] += 1

        for ent in sub.entitlements.filter(status=EntitlementStatus.ACTIVE):
            revoke_entitlement(entitlement=ent, reason="Subscription grace expired")

        for s in HotspotSession.objects.filter(subscription=sub, status=SessionStatus.ACTIVE):
            try:
                disconnect_hotspot_session(
                    session=s,
                    trigger_type=SessionDisconnectTrigger.SUBSCRIPTION_EXPIRED,
                    reason="Subscription grace expired"
                )
            except Exception:
                pass

    return stats
