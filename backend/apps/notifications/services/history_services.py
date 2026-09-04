from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.companies.models import Company

from ..models import NotificationMessage, NotificationStatus
from .sms_services import route_and_send_sms


def mask_phone_number(phone: Optional[str]) -> str:
    """
    Mask phone number for operational privacy (e.g. +25575****012).
    """
    if not phone:
        return ''
    clean = phone.strip()
    if len(clean) <= 6:
        return clean
    if clean.startswith('+'):
        prefix = clean[:6]
        suffix = clean[-3:]
        return f"{prefix}****{suffix}"
    else:
        prefix = clean[:5]
        suffix = clean[-3:]
        return f"{prefix}****{suffix}"


@transaction.atomic
def retry_failed_notification(*, message_id: str, company: Company) -> NotificationMessage:
    """
    Safely retry a failed notification message.
    Rules:
    - Must belong to the requesting company.
    - Status must be FAILED (DELIVERED, SENT, and QUEUED are strictly blocked).
    - Preserves all past attempts and snapshots.
    - Re-enters the standard routing engine to create a new delivery attempt.
    """
    msg = NotificationMessage.objects.filter(id=message_id, company=company).first()
    if not msg:
        raise ValidationError({"message_id": "Notification message not found."})

    if msg.status != NotificationStatus.FAILED:
        raise ValidationError({
            "status": f"Cannot retry message with status '{msg.status}'. Only FAILED messages can be retried."
        })

    # Reset message state to QUEUED
    msg.status = NotificationStatus.QUEUED
    msg.failed_at = None
    msg.save()

    # Re-enter multi-provider routing (preserves previous attempts, appends attempt #N+1)
    processed = route_and_send_sms(notification_message=msg)
    return processed
