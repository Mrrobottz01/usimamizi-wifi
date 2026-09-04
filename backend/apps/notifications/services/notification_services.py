from typing import Optional

from apps.companies.models import Company

from ..models import NotificationChannel, NotificationMessage, NotificationStatus
from .sms_services import route_and_send_sms


def queue_notification(*, company: Company, channel: str = NotificationChannel.SMS, recipient: str, rendered_content: str) -> NotificationMessage:
    """
    Queue a notification message for delivery.
    """
    msg = NotificationMessage.objects.create(
        company=company,
        channel=channel,
        recipient=recipient,
        rendered_content=rendered_content,
        status=NotificationStatus.QUEUED
    )
    return msg


def send_notification(notification_id: str) -> Optional[NotificationMessage]:
    """
    Process and deliver a queued notification message.
    """
    try:
        msg = NotificationMessage.objects.get(id=notification_id)
    except NotificationMessage.DoesNotExist:
        return None

    return route_and_send_sms(notification_message=msg)
