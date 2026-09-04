import logging

from django.utils import timezone

from .models import AccessEntitlement, EntitlementStatus
from .services.entitlement_services import expire_entitlement

logger = logging.getLogger(__name__)


def expire_due_entitlements(batch_size: int = 500) -> int:
    """
    Periodic task to expire due ACTIVE entitlements in bounded batches.
    Idempotent and safe against concurrent executions.
    """
    now = timezone.now()
    due_entitlements = AccessEntitlement.objects.filter(
        status=EntitlementStatus.ACTIVE,
        expires_at__lte=now
    )[:batch_size]

    expired_count = 0
    for entitlement in due_entitlements:
        try:
            expire_entitlement(entitlement=entitlement)
            expired_count += 1
        except Exception as err:
            logger.error("Failed to expire entitlement %s: %s", entitlement.reference, err)

    if expired_count > 0:
        logger.info("Expired %d due entitlements at %s", expired_count, now.isoformat())

    return expired_count
