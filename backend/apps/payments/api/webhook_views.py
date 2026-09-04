import hashlib
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.adapters.snippe_adapter import SnippePaymentAdapter
from apps.payments.models import (
    PaymentProvider,
    PaymentProviderConfiguration,
    PaymentWebhookEvent,
)
from apps.payments.services.purchase_services import (
    process_payment_failure,
    process_verified_payment_completed,
)

logger = logging.getLogger(__name__)


class SnippeWebhookView(APIView):
    """
    POST /api/v1/payments/snippe/webhook/
    Cryptographically verified inbound webhook handler for Snippe Mobile Money events.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        raw_payload = request.body
        signature = request.META.get('HTTP_X_WEBHOOK_SIGNATURE') or ''
        timestamp = request.META.get('HTTP_X_WEBHOOK_TIMESTAMP') or ''

        # 1. Resolve Global or Primary Webhook Secret
        webhook_secret = getattr(settings, 'SNIPPE_WEBHOOK_SECRET', '')
        if not webhook_secret:
            primary_config = PaymentProviderConfiguration.objects.filter(
                provider=PaymentProvider.SNIPPE
            ).exclude(webhook_secret_encrypted='').first()
            if primary_config:
                webhook_secret = primary_config.webhook_secret

        if not webhook_secret:
            logger.error("Snippe webhook received but no SNIPPE_WEBHOOK_SECRET is configured")
            return Response({"error": "Webhook secret not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Cryptographic HMAC-SHA256 Signature Verification
        adapter = SnippePaymentAdapter(
            api_key=getattr(settings, 'SNIPPE_API_KEY', 'dummy'),
            webhook_secret=webhook_secret
        )

        is_valid = adapter.verify_webhook_signature(
            raw_payload=raw_payload,
            signature=signature,
            timestamp=timestamp
        )

        if not is_valid:
            logger.warning("Rejected Snippe webhook: Invalid cryptographic signature.")
            return Response({"error": "Invalid signature."}, status=status.HTTP_401_UNAUTHORIZED)

        # 3. Parse JSON Body
        try:
            payload_data = json.loads(raw_payload.decode('utf-8'))
        except Exception as e:
            logger.error("Failed to parse Snippe webhook JSON payload: %s", e)
            return Response({"error": "Malformed JSON payload."}, status=status.HTTP_400_BAD_REQUEST)

        event_id = payload_data.get('id') or payload_data.get('event_id') or f"evt_{hashlib.sha256(raw_payload).hexdigest()[:24]}"
        event_type = payload_data.get('event') or payload_data.get('type') or 'unknown'
        data_node = payload_data.get('data') or payload_data

        # 4. Idempotency & Deduplication Guard
        existing_event = PaymentWebhookEvent.objects.filter(event_id=event_id).first()
        if existing_event and existing_event.is_processed:
            logger.info("Ignoring duplicate processed webhook event %s", event_id)
            return Response({"status": "duplicate_ignored", "event_id": event_id}, status=status.HTTP_200_OK)

        webhook_event = existing_event or PaymentWebhookEvent.objects.create(
            provider=PaymentProvider.SNIPPE,
            event_id=event_id,
            event_type=event_type,
            signature=signature,
            payload=payload_data
        )

        # 5. Process Event Logic
        provider_ref = str(data_node.get('id') or data_node.get('reference') or '')
        int_ref = data_node.get('reference') or data_node.get('metadata', {}).get('reference')

        raw_amount = data_node.get('amount')
        if isinstance(raw_amount, dict):
            amount_val = raw_amount.get('value')
            currency = raw_amount.get('currency') or data_node.get('currency')
        else:
            amount_val = raw_amount
            currency = data_node.get('currency')

        amount_paid = Decimal(str(amount_val)) if amount_val is not None else None

        try:
            if event_type in ['payment.completed', 'payment.successful', 'payment.paid']:
                txn, purchase, ent = process_verified_payment_completed(
                    provider_reference=provider_ref,
                    internal_reference=int_ref,
                    amount_paid=amount_paid,
                    currency=currency,
                    raw_payload=payload_data
                )
                if not txn:
                    webhook_event.error_message = f"Transaction not found for provider_ref={provider_ref}"
                else:
                    webhook_event.is_processed = True
                    webhook_event.processed_at = timezone.now()

            elif event_type in ['payment.failed', 'payment.expired', 'payment.voided']:
                reason = data_node.get('failure_reason') or data_node.get('message') or event_type
                process_payment_failure(
                    provider_reference=provider_ref,
                    internal_reference=int_ref,
                    failure_reason=reason,
                    raw_payload=payload_data
                )
                webhook_event.is_processed = True
                webhook_event.processed_at = timezone.now()

            else:
                logger.info("Unhandled Snippe webhook event type: %s", event_type)
                webhook_event.is_processed = True
                webhook_event.processed_at = timezone.now()

        except Exception as proc_err:
            logger.exception("Error processing Snippe webhook event %s: %s", event_id, proc_err)
            webhook_event.error_message = str(proc_err)
            webhook_event.save()
            return Response({"error": "Error processing webhook."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        webhook_event.save()
        return Response({"status": "processed", "event_id": event_id}, status=status.HTTP_200_OK)
