import logging
import secrets
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.companies.models import Company, HotspotConfiguration
from apps.entitlements.models import AccessEntitlement, EntitlementSourceType, EntitlementStatus
from apps.entitlements.services.entitlement_services import (
    calculate_entitlement_validity,
    create_plan_snapshot,
)
from apps.notifications.models import NotificationMessage, NotificationStatus
from apps.notifications.services.sms_services import route_and_send_sms
from apps.payments.adapters.base import PaymentProviderAdapter
from apps.payments.adapters.snippe_adapter import SnippePaymentAdapter, normalize_tanzanian_phone
from apps.payments.models import (
    AccessPurchase,
    PaymentAttempt,
    PaymentProvider,
    PaymentProviderConfiguration,
    PaymentStatus,
    PaymentTransaction,
    PurchaseStatus,
)
from apps.plans.models import Plan, ValidityMode
from apps.vouchers.models import Voucher, VoucherBatch, VoucherStatus
from apps.vouchers.selectors.voucher_selectors import hash_voucher_code
from apps.customers.models import (
    Customer,
    CustomerStatus,
    SubscriptionRenewalMode,
    Subscription,
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionSource,
    SubscriptionStatus,
)
from apps.customers.services.customer_services import get_or_create_customer, register_or_update_device
from apps.customers.services.subscription_services import calculate_plan_duration

logger = logging.getLogger(__name__)


def get_payment_config(company: Company) -> PaymentProviderConfiguration:
    """
    Get or create tenant-scoped payment configuration, falling back to environment settings.
    """
    config, _ = PaymentProviderConfiguration.objects.get_or_create(
        company=company,
        provider=PaymentProvider.SNIPPE,
        defaults={
            'is_enabled': True,
            'environment': 'sandbox',
            'api_base_url': getattr(settings, 'SNIPPE_API_BASE_URL', 'https://api.snippe.sh'),
            'default_currency': 'TZS'
        }
    )

    # If database has no API key, check environment settings
    if not config.api_key and getattr(settings, 'SNIPPE_API_KEY', None):
        config.api_key = settings.SNIPPE_API_KEY
        if getattr(settings, 'SNIPPE_WEBHOOK_SECRET', None):
            config.webhook_secret = settings.SNIPPE_WEBHOOK_SECRET
        config.save()

    return config


def get_payment_adapter(config: PaymentProviderConfiguration) -> PaymentProviderAdapter:
    """
    Instantiate appropriate provider adapter.
    """
    api_key = config.api_key or getattr(settings, 'SNIPPE_API_KEY', '')
    webhook_secret = config.webhook_secret or getattr(settings, 'SNIPPE_WEBHOOK_SECRET', '')
    base_url = config.api_base_url or getattr(settings, 'SNIPPE_API_BASE_URL', 'https://api.snippe.sh')

    return SnippePaymentAdapter(
        api_key=api_key,
        webhook_secret=webhook_secret,
        api_base_url=base_url
    )


def generate_purchase_reference() -> str:
    """Generate unique human-readable purchase reference."""
    date_str = timezone.now().strftime("%Y%m%d")
    rand_str = secrets.token_hex(3).upper()
    return f"PUR-{date_str}-{rand_str}"


def generate_transaction_reference() -> str:
    """Generate unique human-readable transaction reference."""
    date_str = timezone.now().strftime("%Y%m%d")
    rand_str = secrets.token_hex(3).upper()
    return f"TXN-{date_str}-{rand_str}"


def generate_idempotency_key() -> str:
    """Generate unique Snippe-compliant idempotency key (max 30 chars)."""
    # 5 prefix + 24 hex = 29 characters <= 30
    return f"idmp_{secrets.token_hex(12)}"


@transaction.atomic
def initiate_access_purchase(
    *,
    company: Company,
    hotspot: Optional[HotspotConfiguration],
    plan: Plan,
    customer_phone: str,
    client_mac: str = '',
    ip_address: Optional[str] = None,
    webhook_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[AccessPurchase, PaymentTransaction, Dict[str, Any]]:
    """
    Initiate customer access purchase:
    1. Validates plan availability.
    2. Normalizes Tanzanian phone number.
    3. Creates AccessPurchase & PaymentTransaction in PENDING state.
    4. Dispatches outbound API call to Snippe Mobile Money.
    5. Returns (purchase, transaction, api_result).
    """
    if not plan.is_active:
        raise ValueError(f"Plan '{plan.name}' is currently inactive.")

    normalized_phone = normalize_tanzanian_phone(customer_phone)
    amount = plan.price
    currency = plan.currency or 'TZS'

    purchase = AccessPurchase.objects.create(
        company=company,
        hotspot=hotspot,
        plan=plan,
        reference=generate_purchase_reference(),
        customer_phone=normalized_phone,
        amount=amount,
        currency=currency,
        status=PurchaseStatus.PAYMENT_PENDING,
        client_mac=client_mac,
        ip_address=ip_address,
        metadata=metadata or {}
    )

    internal_ref = generate_transaction_reference()
    transaction_record = PaymentTransaction.objects.create(
        company=company,
        purchase=purchase,
        provider=PaymentProvider.SNIPPE,
        internal_reference=internal_ref,
        amount=amount,
        currency=currency,
        status=PaymentStatus.PENDING,
        payment_method='mobile',
        customer_phone=normalized_phone
    )

    config = get_payment_config(company)
    adapter = get_payment_adapter(config)

    idempotency_key = generate_idempotency_key()
    attempt = PaymentAttempt.objects.create(
        transaction=transaction_record,
        idempotency_key=idempotency_key,
        request_payload={
            "amount": float(amount),
            "currency": currency,
            "phone_number": normalized_phone,
            "reference": internal_ref
        }
    )

    call_metadata = {
        "purchase_id": str(purchase.id),
        "purchase_reference": purchase.reference,
        "company_id": str(company.id),
        "plan_id": str(plan.id),
        "plan_name": plan.name
    }
    if hotspot:
        call_metadata["hotspot_id"] = str(hotspot.id)

    target_webhook_url = (
        webhook_url
        or getattr(settings, 'SNIPPE_WEBHOOK_URL', None)
        or 'https://wifi.swahilicode.tech/api/v1/payments/snippe/webhook/'
    )

    api_result = adapter.create_payment(
        amount=amount,
        currency=currency,
        phone_number=normalized_phone,
        internal_reference=internal_ref,
        idempotency_key=idempotency_key,
        metadata=call_metadata,
        webhook_url=target_webhook_url
    )

    attempt.response_payload = api_result.raw_response or {}
    attempt.save()

    if api_result.success:
        transaction_record.provider_reference = api_result.provider_reference
        transaction_record.checkout_url = api_result.checkout_url
        transaction_record.payment_link_url = api_result.payment_link_url
        transaction_record.raw_response = api_result.raw_response or {}
        transaction_record.save()
    else:
        transaction_record.status = PaymentStatus.FAILED
        transaction_record.failed_at = timezone.now()
        transaction_record.raw_response = api_result.raw_response or {}
        transaction_record.save()

        purchase.status = PurchaseStatus.FAILED
        purchase.error_message = api_result.error_message
        purchase.save()

    return purchase, transaction_record, {
        "success": api_result.success,
        "provider_reference": api_result.provider_reference,
        "checkout_url": api_result.checkout_url,
        "payment_link_url": api_result.payment_link_url,
        "error_message": api_result.error_message
    }


def _create_voucher_for_entitlement(
    *,
    company: Company,
    plan: Plan,
    entitlement: AccessEntitlement
) -> Voucher:
    """
    Generate an 8-character human-friendly voucher code tied to the paid entitlement.
    Format: XXXX-YYYY
    """
    charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Unambiguous characters
    while True:
        part1 = ''.join(secrets.choice(charset) for _ in range(4))
        part2 = ''.join(secrets.choice(charset) for _ in range(4))
        code = f"{part1}-{part2}"
        if not Voucher.objects.filter(company=company, display_code=code).exists():
            break

    batch, _ = VoucherBatch.objects.get_or_create(
        company=company,
        plan=plan,
        reference=f"VB-PAYMENT-{plan.id.hex[:6].upper()}",
        defaults={
            "label": "Self-Service Purchases",
            "quantity": 0
        }
    )

    voucher = Voucher.objects.create(
        company=company,
        batch=batch,
        plan=plan,
        display_code=code,
        code_hash=hash_voucher_code(code),
        status=VoucherStatus.REDEEMED,
        redeemed_at=timezone.now(),
    )
    entitlement.voucher = voucher
    entitlement.save(update_fields=['voucher'])
    return voucher


@transaction.atomic
def process_verified_payment_completed(
    *,
    provider_reference: str,
    internal_reference: Optional[str] = None,
    amount_paid: Optional[Decimal] = None,
    currency: Optional[str] = None,
    raw_payload: Optional[Dict[str, Any]] = None
) -> Tuple[PaymentTransaction, Optional[AccessPurchase], Optional[AccessEntitlement]]:
    """
    Authoritative payment finalization upon verified Snippe webhook.
    Guarantees:
    1. Idempotency: duplicate webhooks do NOT create duplicate entitlements.
    2. Currency and amount validation against Plan price.
    3. Atomic AccessEntitlement and friendly Voucher code creation.
    4. Isolated SMS delivery confirmation.
    """
    # 1. Resolve PaymentTransaction
    txn_qs = PaymentTransaction.objects.select_for_update().filter(
        models.Q(provider_reference=provider_reference) |
        (models.Q(internal_reference=internal_reference) if internal_reference else models.Q(pk=None))
    )
    transaction_record = txn_qs.first()

    if not transaction_record:
        logger.error("Payment completed webhook for unknown transaction: prov_ref=%s, int_ref=%s", provider_reference, internal_reference)
        return None, None, None

    purchase = transaction_record.purchase

    # 2. Idempotency Guard: if already completed, return existing
    if transaction_record.status == PaymentStatus.COMPLETED and purchase.status == PurchaseStatus.FULFILLED and purchase.entitlement:
        logger.info("Payment already completed and fulfilled for purchase %s", purchase.reference)
        return transaction_record, purchase, purchase.entitlement

    # 3. Amount & Currency Validation
    if amount_paid is not None and amount_paid < transaction_record.amount:
        logger.warning(
            "Underpayment detected on txn %s: expected %s %s, received %s",
            transaction_record.internal_reference, transaction_record.amount, transaction_record.currency, amount_paid
        )
        transaction_record.status = PaymentStatus.FAILED
        transaction_record.failed_at = timezone.now()
        transaction_record.raw_response = raw_payload or {}
        transaction_record.save()

        purchase.status = PurchaseStatus.FAILED
        purchase.error_message = f"Underpayment: expected {transaction_record.amount}, received {amount_paid}"
        purchase.save()
        return transaction_record, purchase, None

    # 4. Finalize Transaction State
    transaction_record.status = PaymentStatus.COMPLETED
    transaction_record.completed_at = timezone.now()
    if raw_payload:
        transaction_record.raw_response = raw_payload
    transaction_record.save()

    # 5. Create AccessEntitlement atomically
    plan = purchase.plan
    plan_snapshot = create_plan_snapshot(plan)

    now = timezone.now()
    activated_at = now
    valid_from, expires_at, usage_time_limit_seconds = calculate_entitlement_validity(plan, now)

    date_str = now.strftime("%Y%m%d")
    ent_ref = f"ENT-{date_str}-{secrets.token_hex(3).upper()}"

    entitlement = AccessEntitlement.objects.create(
        company=purchase.company,
        plan=plan,
        source_type=EntitlementSourceType.PAYMENT,
        status=EntitlementStatus.ACTIVE,
        reference=ent_ref,
        activated_at=activated_at,
        valid_from=valid_from,
        expires_at=expires_at,
        validity_mode=plan.validity_mode,
        usage_time_limit_seconds=usage_time_limit_seconds,
        data_limit_bytes=plan.data_limit_bytes,
        download_speed_kbps=plan.download_speed_kbps,
        upload_speed_kbps=plan.upload_speed_kbps,
        max_devices=plan.max_devices,
        simultaneous_sessions=plan.simultaneous_sessions,
        plan_snapshot=plan_snapshot
    )

    # 6. Generate and attach friendly 8-char Voucher
    voucher = _create_voucher_for_entitlement(
        company=purchase.company,
        plan=plan,
        entitlement=entitlement
    )

    # 6b. Customer & Subscription Linking
    customer = None
    subscription = None
    if purchase.customer_phone:
        try:
            customer, _ = get_or_create_customer(
                company=purchase.company,
                phone=purchase.customer_phone,
            )
            if customer:
                entitlement.consumer = customer

                if purchase.client_mac:
                    register_or_update_device(
                        customer=customer,
                        mac_address=purchase.client_mac,
                    )

                # Check if customer has an existing active or grace subscription for this plan
                existing_sub = Subscription.objects.filter(
                    customer=customer,
                    company=purchase.company,
                    plan=plan,
                    status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE],
                ).order_by('-current_period_end').first()

                if existing_sub:
                    subscription = existing_sub
                    duration = calculate_plan_duration(plan)
                    if existing_sub.status == SubscriptionStatus.ACTIVE and existing_sub.current_period_end and existing_sub.current_period_end > now:
                        new_start = existing_sub.current_period_end
                        new_end = existing_sub.current_period_end + duration
                    else:
                        new_start = now
                        new_end = now + duration

                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.current_period_start = new_start
                    subscription.current_period_end = new_end
                    subscription.grace_period_end = None
                    subscription.save(update_fields=['status', 'current_period_start', 'current_period_end', 'grace_period_end', 'updated_at'])

                    # Update entitlement validity to match extended period
                    entitlement.valid_from = new_start
                    entitlement.expires_at = new_end
                    expires_at = new_end

                    SubscriptionEvent.objects.create(
                        subscription=subscription,
                        event_type=SubscriptionEventType.RENEWED,
                        old_status=existing_sub.status,
                        new_status=SubscriptionStatus.ACTIVE,
                        actor=None,
                        source='PAYMENT',
                        metadata={'purchase_reference': purchase.reference, 'entitlement_reference': ent_ref},
                    )
                else:
                    subscription = Subscription.objects.create(
                        company=purchase.company,
                        customer=customer,
                        plan=plan,
                        hotspot=purchase.hotspot,
                        status=SubscriptionStatus.ACTIVE,
                        started_at=now,
                        current_period_start=valid_from,
                        current_period_end=expires_at,
                        renewal_mode=SubscriptionRenewalMode.MANUAL,
                        source=SubscriptionSource.SELF_SERVICE_PAYMENT,
                        plan_snapshot=plan_snapshot,
                    )
                    SubscriptionEvent.objects.create(
                        subscription=subscription,
                        event_type=SubscriptionEventType.ACTIVATED,
                        old_status=SubscriptionStatus.PENDING,
                        new_status=SubscriptionStatus.ACTIVE,
                        actor=None,
                        source='PAYMENT',
                        metadata={'purchase_reference': purchase.reference, 'entitlement_reference': ent_ref},
                    )

                entitlement.subscription = subscription
                entitlement.save(update_fields=['consumer', 'subscription', 'valid_from', 'expires_at'])
        except Exception as cust_err:
            logger.error("Failed to link customer/subscription for purchase %s: %s", purchase.reference, cust_err)

    # 7. Update AccessPurchase to FULFILLED
    purchase.status = PurchaseStatus.FULFILLED
    purchase.entitlement = entitlement
    purchase.voucher = voucher
    purchase.completed_at = now
    purchase.save()

    # 8. Send SMS Notification (Failure isolated)
    try:
        expiry_display = expires_at.strftime("%Y-%m-%d %H:%M") if expires_at else "Usage-based"
        sms_body = (
            f"Payment confirmed! Plan: {plan.name}. "
            f"Your access code is: {voucher.display_code}. "
            f"Valid until: {expiry_display}. Connect to {purchase.hotspot.ssid if purchase.hotspot else 'Usimamizi Wi-Fi'}."
        )
        sms_record = NotificationMessage.objects.create(
            company=purchase.company,
            channel='SMS',
            recipient=purchase.customer_phone,
            phone_normalized=purchase.customer_phone,
            rendered_content=sms_body,
            status=NotificationStatus.QUEUED,
        )
        route_and_send_sms(notification_message=sms_record)
        logger.info("Purchase confirmation SMS sent to %s for purchase %s", purchase.customer_phone, purchase.reference)
    except Exception as sms_err:
        logger.error("Failed to send purchase confirmation SMS to %s: %s", purchase.customer_phone, sms_err)

    return transaction_record, purchase, entitlement


@transaction.atomic
def process_payment_failure(
    *,
    provider_reference: str,
    internal_reference: Optional[str] = None,
    failure_reason: str = '',
    raw_payload: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[PaymentTransaction], Optional[AccessPurchase]]:
    """
    Handle failed, expired, or voided payment webhook.
    """
    txn_qs = PaymentTransaction.objects.select_for_update().filter(
        models.Q(provider_reference=provider_reference) |
        (models.Q(internal_reference=internal_reference) if internal_reference else models.Q(pk=None))
    )
    transaction_record = txn_qs.first()

    if not transaction_record:
        return None, None

    transaction_record.status = PaymentStatus.FAILED
    transaction_record.failed_at = timezone.now()
    if raw_payload:
        transaction_record.raw_response = raw_payload
    transaction_record.save()

    purchase = transaction_record.purchase
    if purchase.status != PurchaseStatus.FULFILLED:
        purchase.status = PurchaseStatus.FAILED
        purchase.error_message = failure_reason or "Payment failed or expired at provider."
        purchase.save()

    return transaction_record, purchase
