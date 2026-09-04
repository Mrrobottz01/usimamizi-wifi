from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.companies.models import Company, HotspotConfiguration
from apps.entitlements.models import EntitlementSourceType, EntitlementStatus
from apps.payments.models import (
    AccessPurchase,
    PaymentStatus,
    PaymentTransaction,
    PurchaseStatus,
)
from apps.payments.services.purchase_services import (
    initiate_access_purchase,
    process_payment_failure,
    process_verified_payment_completed,
)
from apps.plans.models import Plan, ValidityMode
from apps.vouchers.models import VoucherStatus


@pytest.fixture
def purchase_setup(db):
    company = Company.objects.create(name='Test Payments Co', slug='test-payments-co')
    hotspot = HotspotConfiguration.objects.create(
        company=company,
        name='Main HotSpot',
        slug='test-hotspot',
        ssid='Test-Hotspot-SSID'
    )
    plan = Plan.objects.create(
        company=company,
        name='1 Hour Fast Pass',
        price=Decimal('1000.00'),
        currency='TZS',
        validity_mode=ValidityMode.CONTINUOUS,
        duration_value=60,
        duration_unit='MINUTES',
        download_speed_kbps=5000,
        upload_speed_kbps=2000,
        is_active=True
    )
    return {
        'company': company,
        'hotspot': hotspot,
        'plan': plan
    }


@pytest.mark.django_db
@patch('apps.payments.adapters.snippe_adapter.SnippePaymentAdapter.create_payment')
def test_initiate_access_purchase_success(mock_create_payment, purchase_setup):
    setup = purchase_setup
    mock_create_payment.return_value = MagicMock(
        success=True,
        provider_reference='pay_mock_112233',
        checkout_url='https://checkout.snippe.sh/mock',
        payment_link_url='https://snippe.me/mock',
        raw_response={'id': 'pay_mock_112233'},
        error_message=''
    )

    purchase, txn, res = initiate_access_purchase(
        company=setup['company'],
        hotspot=setup['hotspot'],
        plan=setup['plan'],
        customer_phone='0754123456'
    )

    assert purchase.status == PurchaseStatus.PAYMENT_PENDING
    assert purchase.customer_phone == '+255754123456'
    assert purchase.amount == Decimal('1000.00')
    assert purchase.reference.startswith('PUR-')

    assert txn.status == PaymentStatus.PENDING
    assert txn.provider_reference == 'pay_mock_112233'
    assert txn.internal_reference.startswith('TXN-')
    assert res['success'] is True


@pytest.mark.django_db
@patch('apps.payments.services.purchase_services.route_and_send_sms')
def test_process_verified_payment_completed_creates_entitlement_and_sms(mock_send_sms, purchase_setup):
    setup = purchase_setup
    purchase = AccessPurchase.objects.create(
        company=setup['company'],
        hotspot=setup['hotspot'],
        plan=setup['plan'],
        reference='PUR-20260903-TEST01',
        customer_phone='+255754123456',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PurchaseStatus.PAYMENT_PENDING
    )
    PaymentTransaction.objects.create(
        company=setup['company'],
        purchase=purchase,
        internal_reference='TXN-20260903-TEST01',
        provider_reference='pay_snippe_live_999',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PaymentStatus.PENDING
    )

    completed_txn, fulfilled_pur, entitlement = process_verified_payment_completed(
        provider_reference='pay_snippe_live_999',
        internal_reference='TXN-20260903-TEST01',
        amount_paid=Decimal('1000.00'),
        currency='TZS'
    )

    assert completed_txn.status == PaymentStatus.COMPLETED
    assert fulfilled_pur.status == PurchaseStatus.FULFILLED
    assert entitlement is not None
    assert entitlement.source_type == EntitlementSourceType.PAYMENT
    assert entitlement.status == EntitlementStatus.ACTIVE
    assert entitlement.download_speed_kbps == 5000
    assert entitlement.upload_speed_kbps == 2000
    assert entitlement.plan_snapshot['plan_name'] == '1 Hour Fast Pass'

    # Attached voucher check
    assert fulfilled_pur.voucher is not None
    assert fulfilled_pur.voucher.status == VoucherStatus.REDEEMED
    assert len(fulfilled_pur.voucher.display_code) == 9  # XXXX-YYYY
    assert '-' in fulfilled_pur.voucher.display_code

    # SMS verification
    mock_send_sms.assert_called_once()
    args, kwargs = mock_send_sms.call_args
    if 'notification_message' in kwargs:
        msg = kwargs['notification_message']
        assert msg.recipient == '+255754123456'
        assert fulfilled_pur.voucher.display_code in msg.rendered_content
    else:
        assert kwargs['phone_number'] == '+255754123456'
        assert fulfilled_pur.voucher.display_code in kwargs['message']


@pytest.mark.django_db
@patch('apps.payments.services.purchase_services.route_and_send_sms')
def test_sms_failure_does_not_rollback_access(mock_send_sms, purchase_setup):
    setup = purchase_setup
    mock_send_sms.side_effect = RuntimeError("SMS Provider Gateway Timeout")

    purchase = AccessPurchase.objects.create(
        company=setup['company'],
        hotspot=setup['hotspot'],
        plan=setup['plan'],
        reference='PUR-20260903-TEST02',
        customer_phone='+255754999999',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PurchaseStatus.PAYMENT_PENDING
    )
    PaymentTransaction.objects.create(
        company=setup['company'],
        purchase=purchase,
        internal_reference='TXN-20260903-TEST02',
        provider_reference='pay_snippe_live_888',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PaymentStatus.PENDING
    )

    completed_txn, fulfilled_pur, entitlement = process_verified_payment_completed(
        provider_reference='pay_snippe_live_888',
        internal_reference='TXN-20260903-TEST02',
        amount_paid=Decimal('1000.00'),
        currency='TZS'
    )

    # Entitlement must STILL be active and fulfilled despite SMS failure!
    assert completed_txn.status == PaymentStatus.COMPLETED
    assert fulfilled_pur.status == PurchaseStatus.FULFILLED
    assert entitlement.status == EntitlementStatus.ACTIVE


@pytest.mark.django_db
def test_payment_idempotency_duplicate_webhook_does_not_duplicate_entitlement(purchase_setup):
    setup = purchase_setup
    purchase = AccessPurchase.objects.create(
        company=setup['company'],
        hotspot=setup['hotspot'],
        plan=setup['plan'],
        reference='PUR-20260903-TEST03',
        customer_phone='+255754111222',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PurchaseStatus.PAYMENT_PENDING
    )
    PaymentTransaction.objects.create(
        company=setup['company'],
        purchase=purchase,
        internal_reference='TXN-20260903-TEST03',
        provider_reference='pay_snippe_live_777',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PaymentStatus.PENDING
    )

    # First completion
    txn1, pur1, ent1 = process_verified_payment_completed(
        provider_reference='pay_snippe_live_777',
        internal_reference='TXN-20260903-TEST03',
        amount_paid=Decimal('1000.00')
    )

    # Duplicate completion (e.g. webhook replay)
    txn2, pur2, ent2 = process_verified_payment_completed(
        provider_reference='pay_snippe_live_777',
        internal_reference='TXN-20260903-TEST03',
        amount_paid=Decimal('1000.00')
    )

    assert ent1.id == ent2.id
    assert pur1.voucher.id == pur2.voucher.id
    assert AccessPurchase.objects.filter(customer_phone='+255754111222').count() == 1


@pytest.mark.django_db
def test_underpayment_fails_transaction_and_creates_no_entitlement(purchase_setup):
    setup = purchase_setup
    purchase = AccessPurchase.objects.create(
        company=setup['company'],
        hotspot=setup['hotspot'],
        plan=setup['plan'],
        reference='PUR-20260903-TEST04',
        customer_phone='+255754333444',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PurchaseStatus.PAYMENT_PENDING
    )
    PaymentTransaction.objects.create(
        company=setup['company'],
        purchase=purchase,
        internal_reference='TXN-20260903-TEST04',
        provider_reference='pay_snippe_live_666',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PaymentStatus.PENDING
    )

    # Only 500 TZS paid instead of 1000 TZS
    completed_txn, pur, entitlement = process_verified_payment_completed(
        provider_reference='pay_snippe_live_666',
        internal_reference='TXN-20260903-TEST04',
        amount_paid=Decimal('500.00')
    )

    assert completed_txn.status == PaymentStatus.FAILED
    assert pur.status == PurchaseStatus.FAILED
    assert entitlement is None
    assert 'Underpayment' in pur.error_message


@pytest.mark.django_db
def test_process_payment_failure(purchase_setup):
    setup = purchase_setup
    purchase = AccessPurchase.objects.create(
        company=setup['company'],
        hotspot=setup['hotspot'],
        plan=setup['plan'],
        reference='PUR-20260903-TEST05',
        customer_phone='+255754555666',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PurchaseStatus.PAYMENT_PENDING
    )
    PaymentTransaction.objects.create(
        company=setup['company'],
        purchase=purchase,
        internal_reference='TXN-20260903-TEST05',
        provider_reference='pay_snippe_live_555',
        amount=Decimal('1000.00'),
        currency='TZS',
        status=PaymentStatus.PENDING
    )

    txn, pur = process_payment_failure(
        provider_reference='pay_snippe_live_555',
        failure_reason='Customer cancelled USSD PIN prompt'
    )

    assert txn.status == PaymentStatus.FAILED
    assert pur.status == PurchaseStatus.FAILED
    assert 'Customer cancelled' in pur.error_message
