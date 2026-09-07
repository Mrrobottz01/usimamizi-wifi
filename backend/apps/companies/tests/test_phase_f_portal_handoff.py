import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import HotspotConfiguration
from apps.companies.services.company_services import create_company
from apps.companies.services.portal_services import (
    create_signed_portal_context,
    get_hotspot_login_url,
    validate_destination_url,
    validate_handoff_login_url,
    verify_signed_portal_context,
)
from apps.locations.models import Location
from apps.payments.models import AccessPurchase, PurchaseStatus
from apps.plans.models import DurationUnit, ValidityMode
from apps.plans.services.plan_services import create_plan
from apps.routers.models import Router
from apps.vouchers.services.voucher_services import generate_voucher_batch


@pytest.fixture
def phase_f_setup(db):
    user = User.objects.create_user(email='admin@phase-f-lab.tz', password='Password123!')
    company = create_company(name='Phase F Telecom', user=user)

    location = Location.objects.create(
        company=company,
        name='Dar es Salaam Central',
        code='LOC-DAR-01',
        is_active=True
    )

    router = Router.objects.create(
        company=company,
        location=location,
        name='Main Gateway hAP ac lite',
        identity='MikroTik-Main',
        management_ip='192.168.1.107',
        api_port=8728,
        is_active=True
    )

    plan = create_plan(
        company=company,
        data={
            'name': 'Phase F 1-Hour High Speed',
            'code': 'PF-1H',
            'price': '1000.00',
            'duration_value': 1,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
            'download_speed_kbps': 5120,
            'upload_speed_kbps': 2048,
        }
    )

    # Hotspot A (VLAN 10 - Guest, 10.5.50.1)
    hotspot_a = HotspotConfiguration.objects.create(
        company=company,
        location=location,
        router=router,
        name='Guest HotSpot',
        slug='guest-wifi',
        ssid='Guest-WiFi-Network',
        gateway_ip='10.5.50.1',
        router_login_url='http://10.5.50.1/login',
        default_language='EN',
        is_active=True
    )

    # Hotspot B (VLAN 20 - VIP, 10.5.60.1 on the same router)
    hotspot_b = HotspotConfiguration.objects.create(
        company=company,
        location=location,
        router=router,
        name='VIP Lounge HotSpot',
        slug='vip-lounge',
        ssid='VIP-WiFi-Network',
        gateway_ip='10.5.60.1',
        router_login_url='http://10.5.50.1/login',  # Still default from legacy migration
        default_language='SW',
        is_active=True
    )

    batch, vouchers = generate_voucher_batch(
        company=company,
        plan=plan,
        quantity=3,
        created_by=user
    )

    return {
        'company': company,
        'user': user,
        'location': location,
        'router': router,
        'plan': plan,
        'hotspot_a': hotspot_a,
        'hotspot_b': hotspot_b,
        'vouchers': vouchers,
    }


def test_get_hotspot_login_url_precedence(phase_f_setup):
    hotspot_a = phase_f_setup['hotspot_a']
    hotspot_b = phase_f_setup['hotspot_b']

    # Precedence Tier 1: Validated runtime link-login takes absolute priority
    runtime_ctx = {'link-login': 'http://10.5.50.1/login'}
    assert get_hotspot_login_url(hotspot_a, runtime_ctx) == 'http://10.5.50.1/login'

    # Precedence Tier 3: Hotspot B has gateway 10.5.60.1 but legacy router_login_url is 10.5.50.1.
    # It must derive http://10.5.60.1/login to prevent cross-hotspot misrouting!
    assert get_hotspot_login_url(hotspot_b) == 'http://10.5.60.1/login'

    # Precedence Tier 2: Explicit custom hostname override
    hotspot_a.router_login_url = 'https://hotspot.mycompany.co.tz/login'
    hotspot_a.save()
    assert get_hotspot_login_url(hotspot_a) == 'https://hotspot.mycompany.co.tz/login'


def test_validate_handoff_login_url_security(phase_f_setup):
    hotspot_a = phase_f_setup['hotspot_a']

    # Valid: Exact gateway IP
    assert validate_handoff_login_url('http://10.5.50.1/login', hotspot_a) == 'http://10.5.50.1/login'

    # Valid: Same subnet private IP
    assert validate_handoff_login_url('http://10.5.50.2/login', hotspot_a) == 'http://10.5.50.2/login'

    # Reject: JavaScript injection
    assert validate_handoff_login_url('javascript:alert(1)', hotspot_a) is None

    # Reject: File scheme
    assert validate_handoff_login_url('file:///etc/passwd', hotspot_a) is None

    # Reject: Cloud metadata service SSRF
    assert validate_handoff_login_url('http://169.254.169.254/latest/meta-data', hotspot_a) is None

    # Reject: External attacker domain
    assert validate_handoff_login_url('http://evil-phishing-router.com/login', hotspot_a) is None


def test_validate_destination_url_security():
    # Valid external destination
    assert validate_destination_url('https://www.google.com') == 'https://www.google.com'
    assert validate_destination_url('http://bbc.com/news') == 'http://bbc.com/news'

    # Rejection of dangerous schemes defaults safely to google.com
    assert validate_destination_url('javascript:evil()') == 'https://www.google.com'
    assert validate_destination_url('') == 'https://www.google.com'

    # Rejection of portal self-referential loop
    assert validate_destination_url('https://wifi.operator.tz/p/guest-wifi') == 'https://www.google.com'


def test_signed_portal_context_lifecycle(phase_f_setup):
    hotspot_a = phase_f_setup['hotspot_a']
    hotspot_b = phase_f_setup['hotspot_b']

    runtime_params = {
        'link-login': 'http://10.5.50.1/login',
        'link-orig': 'https://github.com',
        'mac': '56:E9:1A:C4:15:3E',
        'ip': '10.5.50.250',
    }

    token = create_signed_portal_context(hotspot_a, runtime_params)
    assert token is not None

    # Decode and verify with same hotspot
    decoded = verify_signed_portal_context(token, hotspot_a)
    assert decoded is not None
    assert decoded['hotspot_id'] == str(hotspot_a.id)
    assert decoded['gateway_ip'] == '10.5.50.1'
    assert decoded['link_login'] == 'http://10.5.50.1/login'
    assert decoded['mac'] == '56:E9:1A:C4:15:3E'

    # Tampered token fails verification
    assert verify_signed_portal_context(token + 'tampered', hotspot_a) is None

    # Multi-hotspot isolation: Token issued for Hotspot A cannot be verified for Hotspot B
    assert verify_signed_portal_context(token, hotspot_b) is None

    # Expiry test
    assert verify_signed_portal_context(token, hotspot_a, max_age=-1) is None


def test_public_portal_context_endpoint(phase_f_setup):
    client = APIClient()
    hotspot_a = phase_f_setup['hotspot_a']

    res = client.post(f'/api/v1/public/hotspots/{hotspot_a.slug}/portal-context/', {
        'link_login': 'http://10.5.50.1/login',
        'link_orig': 'https://wikipedia.org',
        'mac': '56:E9:1A:C4:15:3E',
        'ip': '10.5.50.250',
    }, format='json')

    assert res.status_code == 200
    data = res.json()
    assert data['login_url'] == 'http://10.5.50.1/login'
    assert data['gateway_ip'] == '10.5.50.1'
    assert 'context_token' in data
    assert data['session_context']['mac'] == '56:E9:1A:C4:15:3E'
    assert data['session_context']['link_orig'] == 'https://wikipedia.org'
    assert len(data['plans']) > 0


def test_disabled_hotspot_rejection(phase_f_setup):
    client = APIClient()
    hotspot_a = phase_f_setup['hotspot_a']
    hotspot_a.is_active = False
    hotspot_a.save()

    res = client.post(f'/api/v1/public/hotspots/{hotspot_a.slug}/portal-context/', {})
    assert res.status_code == 403
    assert res.json()['code'] == 'HOTSPOT_INACTIVE'

    res_portal = client.get(f'/api/v1/public/hotspots/{hotspot_a.slug}/portal/')
    assert res_portal.status_code == 403


def test_voucher_redemption_retains_hotspot_and_safe_retry(phase_f_setup):
    client = APIClient()
    hotspot_a = phase_f_setup['hotspot_a']
    voucher = phase_f_setup['vouchers'][0]

    # First redemption with signed context
    token = create_signed_portal_context(hotspot_a, {'link-login': 'http://10.5.50.1/login'})

    res1 = client.post(f'/api/v1/public/hotspots/{hotspot_a.slug}/voucher/', {
        'voucher_code': voucher.display_code,
        'context_token': token,
    }, format='json')

    assert res1.status_code == 200
    data1 = res1.json()
    assert data1['success'] is True
    assert data1['router_login_url'] == 'http://10.5.50.1/login'
    assert data1['gateway_ip'] == '10.5.50.1'

    # Safe Retry: Customer clicks "Retry Connection" on handoff failure.
    # The voucher was already redeemed, but system returns the existing active entitlement safely!
    res2 = client.post(f'/api/v1/public/hotspots/{hotspot_a.slug}/voucher/', {
        'voucher_code': voucher.display_code,
        'context_token': token,
    }, format='json')

    assert res2.status_code == 200
    data2 = res2.json()
    assert data2['success'] is True
    assert data2['entitlement_reference'] == data1['entitlement_reference']
    assert data2['router_login_url'] == 'http://10.5.50.1/login'


def test_purchase_status_returns_hotspot_router_login_url(phase_f_setup):
    client = APIClient()
    company = phase_f_setup['company']
    hotspot_b = phase_f_setup['hotspot_b']
    plan = phase_f_setup['plan']

    purchase = AccessPurchase.objects.create(
        company=company,
        hotspot=hotspot_b,
        plan=plan,
        reference='PUR-PHASE-F-TEST01',
        customer_phone='255712345678',
        amount=plan.price,
        currency='TZS',
        status=PurchaseStatus.FULFILLED
    )

    res = client.get(f'/api/v1/public/purchases/{purchase.reference}/status/')
    assert res.status_code == 200
    data = res.json()
    # Hotspot B's gateway is 10.5.60.1
    assert data['router_login_url'] == 'http://10.5.60.1/login'
    assert data['gateway_ip'] == '10.5.60.1'
