import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.payments.models import (
    PaymentProviderConfiguration,
    PaymentStatus,
    PaymentTransaction,
)
from apps.payments.services.purchase_services import (
    get_payment_adapter,
    process_payment_failure,
    process_verified_payment_completed,
)

logger = logging.getLogger(__name__)


@shared_task(name="reconcile_stuck_payments")
def reconcile_stuck_payments(max_age_minutes: int = 120, min_age_minutes: int = 3):
    """
    Periodic task to poll provider for pending transactions that may have missed a webhook.
    """
    now = timezone.now()
    threshold_min = now - timedelta(minutes=min_age_minutes)
    threshold_max = now - timedelta(minutes=max_age_minutes)

    stuck_txns = PaymentTransaction.objects.filter(
        status=PaymentStatus.PENDING,
        created_at__lte=threshold_min,
        created_at__gte=threshold_max
    ).exclude(provider_reference='')

    logger.info("Found %d pending transactions to reconcile with Snippe", stuck_txns.count())

    for txn in stuck_txns:
        try:
            config = PaymentProviderConfiguration.objects.filter(
                company=txn.company,
                provider=txn.provider
            ).first()
            if not config:
                continue

            adapter = get_payment_adapter(config)
            res = adapter.get_payment_status(txn.provider_reference)

            if res.status == PaymentStatus.COMPLETED:
                logger.info("Reconciliation found completed payment for %s", txn.internal_reference)
                process_verified_payment_completed(
                    provider_reference=txn.provider_reference,
                    internal_reference=txn.internal_reference,
                    amount_paid=res.amount,
                    currency=res.currency,
                    raw_payload=res.raw_response
                )
            elif res.status in [PaymentStatus.FAILED, PaymentStatus.EXPIRED, PaymentStatus.CANCELLED]:
                logger.info("Reconciliation found %s payment for %s", res.status, txn.internal_reference)
                process_payment_failure(
                    provider_reference=txn.provider_reference,
                    internal_reference=txn.internal_reference,
                    failure_reason=res.error_message or f"Reconciled status: {res.status}",
                    raw_payload=res.raw_response
                )
        except Exception as e:
            logger.exception("Error reconciling transaction %s: %s", txn.internal_reference, e)
