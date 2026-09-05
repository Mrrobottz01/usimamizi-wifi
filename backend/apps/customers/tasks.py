import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.notifications.models import NotificationMessage, NotificationStatus
from apps.notifications.services.sms_services import route_and_send_sms
from .models import (
    CustomerSubscriptionSettings,
    Subscription,
    SubscriptionStatus,
)
from .services.subscription_services import process_subscription_expiries

logger = logging.getLogger(__name__)


@shared_task(name="process_subscription_expiries_task")
def process_subscription_expiries_task():
    """
    Evaluates active and grace subscriptions, transitions expired states,
    revokes entitlements, and issues RFC 3576 disconnect requests.
    """
    stats = process_subscription_expiries()
    logger.info("Subscription expiries processed: %s", stats)
    return stats


@shared_task(name="send_subscription_renewal_reminders_task")
def send_subscription_renewal_reminders_task():
    """
    Sends proactive SMS renewal reminders to customers whose active subscriptions
    are approaching expiration (1 day before or 1 hour before).
    """
    now = timezone.now()
    reminders_sent = 0

    # 1. 24-hour reminder window (between 23h and 25h from now)
    day_window_start = now + timedelta(hours=23)
    day_window_end = now + timedelta(hours=25)

    subs_1day = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        current_period_end__gte=day_window_start,
        current_period_end__lte=day_window_end,
    ).select_related('customer', 'company', 'plan', 'hotspot')

    for sub in subs_1day:
        settings_obj, _ = CustomerSubscriptionSettings.objects.get_or_create(company=sub.company)
        if not settings_obj.remind_1day_before:
            continue

        # Prevent duplicate reminders via unique tag/check
        already_sent = NotificationMessage.objects.filter(
            company=sub.company,
            recipient=sub.customer.normalized_phone,
            rendered_content__icontains=f"expires tomorrow",
            created_at__gte=now - timedelta(hours=20),
        ).exists()

        if already_sent:
            continue

        brand = sub.hotspot.brand_name if (sub.hotspot and sub.hotspot.brand_name) else sub.company.name
        end_time_str = sub.current_period_end.strftime("%d/%m/%Y %H:%M")
        msg_text = (
            f"{brand}: Your Wi-Fi plan ({sub.plan.name}) expires tomorrow at {end_time_str}. "
            f"Renew now to maintain uninterrupted internet access."
        )

        try:
            sms_record = NotificationMessage.objects.create(
                company=sub.company,
                channel='SMS',
                recipient=sub.customer.normalized_phone,
                phone_normalized=sub.customer.normalized_phone,
                rendered_content=msg_text,
                status=NotificationStatus.QUEUED,
            )
            route_and_send_sms(notification_message=sms_record)
            reminders_sent += 1
        except Exception as err:
            logger.error("Failed to send 1-day reminder to %s: %s", sub.customer.normalized_phone, err)

    # 2. 1-hour reminder window (between 50m and 70m from now)
    hour_window_start = now + timedelta(minutes=50)
    hour_window_end = now + timedelta(minutes=70)

    subs_1hour = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        current_period_end__gte=hour_window_start,
        current_period_end__lte=hour_window_end,
    ).select_related('customer', 'company', 'plan', 'hotspot')

    for sub in subs_1hour:
        settings_obj, _ = CustomerSubscriptionSettings.objects.get_or_create(company=sub.company)
        if not settings_obj.remind_1hour_before:
            continue

        already_sent = NotificationMessage.objects.filter(
            company=sub.company,
            recipient=sub.customer.normalized_phone,
            rendered_content__icontains=f"expires in 1 hour",
            created_at__gte=now - timedelta(minutes=90),
        ).exists()

        if already_sent:
            continue

        brand = sub.hotspot.brand_name if (sub.hotspot and sub.hotspot.brand_name) else sub.company.name
        end_time_str = sub.current_period_end.strftime("%H:%M")
        msg_text = (
            f"{brand}: Your Wi-Fi plan ({sub.plan.name}) expires in 1 hour (at {end_time_str}). "
            f"Renew now to avoid disconnection."
        )

        try:
            sms_record = NotificationMessage.objects.create(
                company=sub.company,
                channel='SMS',
                recipient=sub.customer.normalized_phone,
                phone_normalized=sub.customer.normalized_phone,
                rendered_content=msg_text,
                status=NotificationStatus.QUEUED,
            )
            route_and_send_sms(notification_message=sms_record)
            reminders_sent += 1
        except Exception as err:
            logger.error("Failed to send 1-hour reminder to %s: %s", sub.customer.normalized_phone, err)

    return {"reminders_sent": reminders_sent}
