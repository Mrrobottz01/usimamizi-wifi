import hashlib
import hmac
import json
import time
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.companies.models import Company, HotspotConfiguration
from apps.payments.models import (
    AccessPurchase,
    PaymentProviderConfiguration,
    PaymentStatus,
    PaymentTransaction,
    PaymentWebhookEvent,
    PurchaseStatus,
)
from apps.plans.models import Plan, ValidityMode


@pytest.fixture
def webhook_setup(db, settings):
    settings.SNIPPE_WEBHOOK_SECRET = 'whsec_test_secret_abc123'
    company = Company.objects.create(name='Webhook Co', slug='webhook-co')
    hotspot = HotspotConfiguration.objects.create(
        company=company,
        name='Webhook HotSpot',
        slug='webhook-hotspot'
    )
    plan = Plan.objects.create(
        company=company,
        name='Daily Pass',
        price=Decimal('2000.00'),
        currency='TZS',
        validity_mode=ValidityMode.CONTINUOUS,
        duration_value=1,
        duration_unit='DAYS',
        is_active=True
    )
    purchase = AccessPurchase.objects.create(
        company=company,
        hotspot=hotspot,
        plan=plan,
        reference='PUR-20260903-WH001',
        customer_phone='+255754000111',
        amount=Decimal('2000.00'),
        status=PurchaseStatus.PAYMENT_PENDING
    )
    txn = PaymentTransaction.objects.create(
        company=company,
        purchase=purchase,
        internal_reference='TXN-20260903-WH001',
        provider_reference='pay_webhook_test_1',
        amount=Decimal('2000.00'),
        status=PaymentStatus.PENDING
    )
    PaymentProviderConfiguration.objects.create(
        company=company,
        api_key_encrypted='dummy',
        webhook_secret_encrypted='whsec_test_secret_abc123'
    )
    return {
        'company': company,
        'purchase': purchase,
        'txn': txn,
        'secret': 'whsec_test_secret_abc123'
    }


def _generate_sig(payload_bytes: bytes, secret: str, timestamp: str) -> str:
    to_sign = timestamp.encode('utf-8') + b'.' + payload_bytes
    return hmac.new(secret.encode('utf-8'), to_sign, hashlib.sha256).hexdigest()


@pytest.mark.django_db
def test_webhook_successful_payment_completed(webhook_setup):
    client = APIClient()
    url = reverse('snippe-webhook')

    payload = {
        "event": "payment.completed",
        "id": "evt_unique_test_101",
        "data": {
            "id": "pay_webhook_test_1",
            "reference": "TXN-20260903-WH001",
            "amount": 2000.00,
            "currency": "TZS",
            "status": "completed"
        }
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    ts = str(int(time.time()))
    sig = _generate_sig(payload_bytes, webhook_setup['secret'], ts)

    resp = client.post(
        url,
        data=payload_bytes,
        content_type='application/json',
        HTTP_X_WEBHOOK_SIGNATURE=sig,
        HTTP_X_WEBHOOK_TIMESTAMP=ts
    )

    assert resp.status_code == 200
    assert resp.data['status'] == 'processed'

    # Verify database state
    txn = PaymentTransaction.objects.get(id=webhook_setup['txn'].id)
    purchase = AccessPurchase.objects.get(id=webhook_setup['purchase'].id)

    assert txn.status == PaymentStatus.COMPLETED
    assert purchase.status == PurchaseStatus.FULFILLED
    assert purchase.entitlement is not None
    assert purchase.voucher is not None

    # Webhook audit log
    event_log = PaymentWebhookEvent.objects.get(event_id='evt_unique_test_101')
    assert event_log.is_processed is True


@pytest.mark.django_db
def test_webhook_invalid_signature_rejected(webhook_setup):
    client = APIClient()
    url = reverse('snippe-webhook')

    payload = {"event": "payment.completed", "id": "evt_tampered"}
    payload_bytes = json.dumps(payload).encode('utf-8')
    ts = str(int(time.time()))

    resp = client.post(
        url,
        data=payload_bytes,
        content_type='application/json',
        HTTP_X_WEBHOOK_SIGNATURE='forged_tampered_signature_hex',
        HTTP_X_WEBHOOK_TIMESTAMP=ts
    )

    assert resp.status_code == 401
    assert resp.data['error'] == 'Invalid signature.'


@pytest.mark.django_db
def test_webhook_deduplication(webhook_setup):
    client = APIClient()
    url = reverse('snippe-webhook')

    payload = {
        "event": "payment.completed",
        "id": "evt_duplicate_test_202",
        "data": {
            "id": "pay_webhook_test_1",
            "reference": "TXN-20260903-WH001",
            "amount": 2000.00,
            "currency": "TZS"
        }
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    ts = str(int(time.time()))
    sig = _generate_sig(payload_bytes, webhook_setup['secret'], ts)

    # First call
    resp1 = client.post(
        url,
        data=payload_bytes,
        content_type='application/json',
        HTTP_X_WEBHOOK_SIGNATURE=sig,
        HTTP_X_WEBHOOK_TIMESTAMP=ts
    )
    assert resp1.status_code == 200
    assert resp1.data['status'] == 'processed'

    # Replay call
    resp2 = client.post(
        url,
        data=payload_bytes,
        content_type='application/json',
        HTTP_X_WEBHOOK_SIGNATURE=sig,
        HTTP_X_WEBHOOK_TIMESTAMP=ts
    )
    assert resp2.status_code == 200
    assert resp2.data['status'] == 'duplicate_ignored'
