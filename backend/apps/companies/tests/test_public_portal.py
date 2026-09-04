import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import HotspotConfiguration
from apps.companies.services.company_services import create_company
from apps.companies.services.portal_services import (
    get_customer_error_message,
)
from apps.entitlements.models import EntitlementStatus
from apps.plans.models import DurationUnit, ValidityMode
from apps.plans.services.plan_services import create_plan
from apps.vouchers.models import VoucherStatus
from apps.vouchers.services.voucher_services import generate_voucher_batch


@pytest.fixture
def portal_setup():
    user = User.objects.create_user(email='owner@hotspotlab.co.tz', password='Password123!')
    company = create_company(name='HotSpot Lab Co', user=user)

    plan = create_plan(
        company=company,
        data={
            'name': 'Portal Standard 1H',
            'code': 'PORTAL-1H',
            'price': '1000.00',
            'duration_value': 1,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
            'download_speed_kbps': 5120,
            'upload_speed_kbps': 2048,
            'max_devices': 2,
            'simultaneous_sessions': 1,
        }
    )

    batch, vouchers = generate_voucher_batch(
        company=company,
        plan=plan,
        quantity=5,
        created_by=user
    )

    hotspot = HotspotConfiguration.objects.create(
        company=company,
        name='Lab HotSpot Zinga',
        slug='lab-zinga',
        ssid='HotSpot-Lab-WiFi',
        brand_name='Lab Zinga Wi-Fi',
        headline='Karibu Lab Zinga Wi-Fi',
        welcome_text='Weka nambari ya vocha yako kuanza.',
        primary_color='#10b981',
        support_phone='+255 712 345 678',
        default_language='SW',
        is_active=True
    )

    return {
        'user': user,
        'company': company,
        'plan': plan,
        'batch': batch,
        'hotspot': hotspot,
        'vouchers': vouchers
    }


@pytest.mark.django_db
def test_public_hotspot_portal_config_success(portal_setup):
    setup = portal_setup
    client = APIClient()

    resp = client.get(f"/api/v1/public/hotspots/{setup['hotspot'].slug}/portal/")
    assert resp.status_code == 200
    assert resp.data['slug'] == 'lab-zinga'
    assert resp.data['brand_name'] == 'Lab Zinga Wi-Fi'
    assert resp.data['company_name'] == setup['company'].name
    assert resp.data['primary_color'] == '#10b981'
    assert 'shared_secret' not in resp.data


@pytest.mark.django_db
def test_public_hotspot_portal_config_inactive_and_not_found(portal_setup):
    setup = portal_setup
    client = APIClient()

    # Inactive HotSpot
    setup['hotspot'].is_active = False
    setup['hotspot'].save()

    resp = client.get(f"/api/v1/public/hotspots/{setup['hotspot'].slug}/portal/")
    assert resp.status_code == 403
    assert resp.data['code'] == 'HOTSPOT_INACTIVE'

    # Nonexistent HotSpot
    resp404 = client.get("/api/v1/public/hotspots/non-existent-hotspot/portal/")
    assert resp404.status_code == 404


@pytest.mark.django_db
def test_public_voucher_redeem_available_success(portal_setup):
    setup = portal_setup
    client = APIClient()
    voucher = setup['vouchers'][0]

    resp = client.post(
        f"/api/v1/public/hotspots/{setup['hotspot'].slug}/voucher/",
        {
            'voucher_code': voucher.display_code,
            'language': 'EN'
        },
        format='json'
    )
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['username'] == voucher.display_code
    assert resp.data['password'] == voucher.display_code
    assert resp.data['download_speed_kbps'] == 5120
    assert resp.data['remaining_seconds'] is not None

    voucher.refresh_from_db()
    assert voucher.status == VoucherStatus.REDEEMED
    assert hasattr(voucher, 'entitlement')
    assert voucher.entitlement.status == EntitlementStatus.ACTIVE


@pytest.mark.django_db
def test_public_voucher_redeem_already_redeemed_authorizable(portal_setup):
    setup = portal_setup
    client = APIClient()
    voucher = setup['vouchers'][0]

    # First redemption
    client.post(
        f"/api/v1/public/hotspots/{setup['hotspot'].slug}/voucher/",
        {'voucher_code': voucher.display_code},
        format='json'
    )

    # Subsequent login attempt using existing active entitlement
    resp2 = client.post(
        f"/api/v1/public/hotspots/{setup['hotspot'].slug}/voucher/",
        {'voucher_code': voucher.display_code},
        format='json'
    )
    assert resp2.status_code == 200
    assert resp2.data['success'] is True
    assert resp2.data['username'] == voucher.display_code


@pytest.mark.django_db
def test_public_voucher_tenant_isolation(portal_setup):
    setup = portal_setup
    client = APIClient()

    # Create Company B with another hotspot and batch
    user_b = User.objects.create_user(email='other@companyb.com', password='Password123!')
    company_b = create_company(name='Company B', user=user_b)
    plan_b = create_plan(
        company=company_b,
        data={
            'name': 'Company B Plan',
            'code': 'COMPB-1H',
            'price': '2000.00',
            'duration_value': 1,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
        }
    )
    batch_b, vouchers_b = generate_voucher_batch(company=company_b, plan=plan_b, quantity=1, created_by=user_b)
    voucher_b = vouchers_b[0]

    # Attempting to submit Company B's voucher to Company A's hotspot must fail
    resp = client.post(
        f"/api/v1/public/hotspots/{setup['hotspot'].slug}/voucher/",
        {'voucher_code': voucher_b.display_code, 'language': 'EN'},
        format='json'
    )
    assert resp.status_code == 400
    assert resp.data['success'] is False
    assert resp.data['error_code'] == 'NOT_FOUND'
    assert 'not found for this network' in resp.data['message'].lower()


@pytest.mark.django_db
def test_bilingual_customer_error_messages():
    # Test Swahili error mapping
    msg_sw = get_customer_error_message('DEVICE_LIMIT_REACHED', lang='SW')
    assert 'Vocha hii tayari imeunganishwa' in msg_sw

    # Test English error mapping
    msg_en = get_customer_error_message('DEVICE_LIMIT_REACHED', lang='EN')
    assert 'maximum number of devices' in msg_en


@pytest.mark.django_db
def test_admin_hotspot_settings_view(portal_setup):
    setup = portal_setup
    client = APIClient()
    client.force_authenticate(user=setup['user'])

    # GET settings
    resp = client.get(f"/api/v1/settings/hotspot/?company_id={setup['company'].id}")
    assert resp.status_code == 200
    assert resp.data['slug'] == 'lab-zinga'

    # PUT settings
    put_resp = client.put(
        f"/api/v1/settings/hotspot/?company_id={setup['company'].id}",
        {
            'headline': 'Updated Welcome Message',
            'primary_color': '#6366f1',
        },
        format='json'
    )
    assert put_resp.status_code == 200
    assert put_resp.data['headline'] == 'Updated Welcome Message'
    assert put_resp.data['primary_color'] == '#6366f1'
