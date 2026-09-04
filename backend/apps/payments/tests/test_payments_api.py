from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.companies.models import Company, CompanyMembership, HotspotConfiguration
from apps.payments.models import (
    AccessPurchase,
    PaymentStatus,
    PaymentTransaction,
    PurchaseStatus,
)
from apps.plans.models import Plan, ValidityMode

User = get_user_model()


@pytest.fixture
def api_setup(db):
    company = Company.objects.create(name='API Co', slug='api-co')
    user = User.objects.create_user(email='admin@api.com', password='password123', first_name='Admin', last_name='User')
    CompanyMembership.objects.create(company=company, user=user, is_active=True)

    other_company = Company.objects.create(name='Other Co', slug='other-co')

    hotspot = HotspotConfiguration.objects.create(
        company=company,
        name='API Hotspot',
        slug='api-hotspot'
    )
    plan = Plan.objects.create(
        company=company,
        name='Test Plan 5K',
        price=Decimal('5000.00'),
        currency='TZS',
        validity_mode=ValidityMode.CONTINUOUS,
        duration_value=1,
        duration_unit='DAYS',
        is_active=True
    )
    return {
        'company': company,
        'other_company': other_company,
        'user': user,
        'hotspot': hotspot,
        'plan': plan
    }


@pytest.mark.django_db
def test_public_hotspot_plans_list(api_setup):
    client = APIClient()
    url = reverse('public-hotspot-plans', kwargs={'slug': 'api-hotspot'})

    resp = client.get(url)
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]['name'] == 'Test Plan 5K'
    assert float(resp.data[0]['price']) == 5000.00


@pytest.mark.django_db
@patch('apps.payments.adapters.snippe_adapter.SnippePaymentAdapter.create_payment')
def test_public_initiate_purchase_and_poll_status(mock_create_payment, api_setup):
    setup = api_setup
    mock_create_payment.return_value = MagicMock(
        success=True,
        provider_reference='pay_api_test_01',
        checkout_url='https://checkout.snippe.sh/api_test_01',
        payment_link_url='',
        raw_response={'id': 'pay_api_test_01'}
    )

    client = APIClient()
    initiate_url = reverse('public-hotspot-purchase-initiate', kwargs={'slug': 'api-hotspot'})

    resp = client.post(initiate_url, {
        'plan_id': str(setup['plan'].id),
        'customer_phone': '0754987654'
    })

    assert resp.status_code == 201
    purchase_ref = resp.data['purchase_reference']
    assert purchase_ref.startswith('PUR-')

    # Poll status
    status_url = reverse('public-purchase-status', kwargs={'reference': purchase_ref})
    poll_resp = client.get(status_url)

    assert poll_resp.status_code == 200
    assert poll_resp.data['status'] == PurchaseStatus.PAYMENT_PENDING
    assert poll_resp.data['plan_name'] == 'Test Plan 5K'
    assert poll_resp.data['checkout_url'] == 'https://checkout.snippe.sh/api_test_01'


@pytest.mark.django_db
def test_admin_payments_and_tenant_isolation(api_setup):
    setup = api_setup
    client = APIClient()
    client.force_authenticate(user=setup['user'])

    # Create transaction for company
    purchase = AccessPurchase.objects.create(
        company=setup['company'],
        plan=setup['plan'],
        reference='PUR-OWN-01',
        customer_phone='+255754111222',
        amount=Decimal('5000.00'),
        status=PurchaseStatus.PAYMENT_PENDING
    )
    PaymentTransaction.objects.create(
        company=setup['company'],
        purchase=purchase,
        internal_reference='TXN-OWN-01',
        amount=Decimal('5000.00'),
        status=PaymentStatus.PENDING
    )

    # Create transaction for other company
    other_purchase = AccessPurchase.objects.create(
        company=setup['other_company'],
        plan=setup['plan'],
        reference='PUR-OTHER-01',
        customer_phone='+255754333444',
        amount=Decimal('5000.00'),
        status=PurchaseStatus.PAYMENT_PENDING
    )
    PaymentTransaction.objects.create(
        company=setup['other_company'],
        purchase=other_purchase,
        internal_reference='TXN-OTHER-01',
        amount=Decimal('5000.00'),
        status=PaymentStatus.PENDING
    )

    url = reverse('payment-list')
    resp = client.get(url, {'company_id': str(setup['company'].id)})

    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['internal_reference'] == 'TXN-OWN-01'

    # Unauthorized company access
    resp_other = client.get(url, {'company_id': str(setup['other_company'].id)})
    assert resp_other.status_code == 403


@pytest.mark.django_db
def test_admin_payment_settings_masking(api_setup):
    setup = api_setup
    client = APIClient()
    client.force_authenticate(user=setup['user'])

    url = reverse('payment-settings')

    # Update credentials
    put_resp = client.put(url, {
        'company_id': str(setup['company'].id),
        'api_key': 'snippe_secret_key_123456789',
        'webhook_secret': 'whsec_987654321_secret',
        'environment': 'live'
    })
    assert put_resp.status_code == 200
    assert 'api_key' not in put_resp.data  # Write-only
    assert '••••' in put_resp.data['api_key_masked']
    assert '••••' in put_resp.data['webhook_secret_masked']
    assert put_resp.data['environment'] == 'live'


@pytest.mark.django_db
def test_admin_walled_garden_preset_and_export(api_setup):
    setup = api_setup
    client = APIClient()
    client.force_authenticate(user=setup['user'])

    apply_url = reverse('walled-garden-preset-apply')
    resp = client.post(apply_url, {
        'company_id': str(setup['company'].id),
        'preset_name': 'Snippe Payments'
    })
    assert resp.status_code == 200
    assert resp.data['entries_count'] == 3

    export_url = reverse('walled-garden-export-routeros')
    export_resp = client.get(export_url, {'company_id': str(setup['company'].id)})
    assert export_resp.status_code == 200
    assert '/ip hotspot walled-garden add dst-host="api.snippe.sh"' in export_resp.data['script']
