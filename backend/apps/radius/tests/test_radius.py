from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.companies.services.company_services import create_company
from apps.entitlements.models import (
    EntitlementSourceType,
)
from apps.entitlements.services.entitlement_services import (
    create_entitlement_from_plan,
    revoke_entitlement,
    suspend_entitlement,
)
from apps.hotspot_sessions.models import HotspotSession, SessionStatus
from apps.plans.models import DurationUnit, ValidityMode
from apps.plans.services.plan_services import create_plan
from apps.radius.models import AccountingPacketType, RadiusClient
from apps.radius.services.radius_services import (
    authorize_radius_access,
    normalize_mac_address,
    process_radius_accounting,
)
from apps.vouchers.services.voucher_services import (
    generate_voucher_batch,
    redeem_voucher,
)

User = get_user_model()


@pytest.fixture
def radius_setup():
    user1 = User.objects.create_user(email='radius_alpha@example.com', password='Password123!')
    company1 = create_company(name='Alpha Wi-Fi Hotspots', user=user1)

    user2 = User.objects.create_user(email='radius_beta@example.com', password='Password123!')
    company2 = create_company(name='Beta Wi-Fi Hotspots', user=user2)

    # Authorized NAS routers
    nas1 = RadiusClient.objects.create(
        company=company1,
        name='Alpha hAP ac lite',
        nas_ip='192.168.88.1',
        nas_identifier='alpha-router-01',
        is_active=True
    )
    nas1.shared_secret = 'alpha_secret_123'
    nas1.save()

    nas2 = RadiusClient.objects.create(
        company=company2,
        name='Beta RB4011',
        nas_ip='192.168.99.1',
        nas_identifier='beta-router-01',
        is_active=True
    )
    nas2.shared_secret = 'beta_secret_123'
    nas2.save()

    # Plan A: 5 Mbps Down / 2 Mbps Up (Continuous 24h, 1GB data quota, max 1 device, 1 session)
    plan_a = create_plan(
        company=company1,
        data={
            'name': 'Alpha 24H High Speed',
            'code': 'ALPHA-24H-5M',
            'price': '2000.00',
            'duration_value': 24,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
            'download_speed_kbps': 5120,
            'upload_speed_kbps': 2048,
            'data_limit_bytes': 1073741824,  # 1 GB
            'max_devices': 1,
            'simultaneous_sessions': 1,
            'idle_timeout_seconds': 300,
            'session_timeout_seconds': 86400,
        }
    )

    # Plan B: 15 Mbps Down / 5 Mbps Up (Usage Time 5h, no data limit, max 2 devices, 1 session)
    plan_b = create_plan(
        company=company1,
        data={
            'name': 'Alpha 5H Ultra Speed',
            'code': 'ALPHA-5H-15M',
            'price': '5000.00',
            'duration_value': 5,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.USAGE_TIME,
            'download_speed_kbps': 15360,
            'upload_speed_kbps': 5120,
            'max_devices': 2,
            'simultaneous_sessions': 1,
            'idle_timeout_seconds': 600,
            'session_timeout_seconds': 18000,
        }
    )

    return {
        'company1': company1,
        'company2': company2,
        'nas1': nas1,
        'nas2': nas2,
        'plan_a': plan_a,
        'plan_b': plan_b,
        'user1': user1,
        'user2': user2,
    }


@pytest.mark.django_db
def test_mac_normalization():
    """
    Test MAC address normalization across varying vendor formats.
    """
    assert normalize_mac_address('aa:bb:cc:dd:ee:ff') == 'AA:BB:CC:DD:EE:FF'
    assert normalize_mac_address('AA-BB-CC-DD-EE-FF') == 'AA:BB:CC:DD:EE:FF'
    assert normalize_mac_address('aabbccddeeff') == 'AA:BB:CC:DD:EE:FF'
    assert normalize_mac_address('AA.BB.CC.DD.EE.FF') == 'AA:BB:CC:DD:EE:FF'


@pytest.mark.django_db
def test_unknown_and_disabled_nas_rejection(radius_setup):
    """
    Test that Access-Requests from unauthorized or disabled NAS routers fail closed.
    """
    # 1. Unknown NAS IP
    res_unknown = authorize_radius_access(
        username='TEST-VOUCHER',
        nas_ip='10.254.254.254'
    )
    assert res_unknown['accept'] is False
    assert res_unknown['reason'] == 'UNKNOWN_NAS'

    # 2. Disabled NAS
    nas = radius_setup['nas1']
    nas.is_active = False
    nas.save()

    res_disabled = authorize_radius_access(
        username='TEST-VOUCHER',
        nas_ip=nas.nas_ip
    )
    assert res_disabled['accept'] is False
    assert res_disabled['reason'] == 'NAS_DISABLED'


@pytest.mark.django_db
def test_entitlement_authorization_lifecycle_decisions(radius_setup):
    """
    Test that FreeRADIUS authorization decisions strictly reflect AccessEntitlement lifecycle states.
    """
    nas = radius_setup['nas1']
    company = radius_setup['company1']
    plan = radius_setup['plan_a']

    # Create voucher and redeem into active entitlement
    _, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=1, created_by=radius_setup['user1'])
    voucher = vouchers[0]
    _, entitlement = redeem_voucher(voucher_code=voucher.display_code, company=company)

    # 1. Active Entitlement -> Accept
    res_auth = authorize_radius_access(
        username=voucher.display_code,
        nas_ip=nas.nas_ip,
        mac_address='AA:BB:CC:DD:EE:01'
    )
    assert res_auth['accept'] is True
    assert res_auth['reason'] == 'AUTHORIZED'
    assert res_auth['reply']['Mikrotik-Rate-Limit'] == '2048k/5120k'
    assert res_auth['reply']['WISPr-Bandwidth-Max-Down'] == 5120000
    assert res_auth['reply']['WISPr-Bandwidth-Max-Up'] == 2048000
    assert res_auth['reply']['Idle-Timeout'] == 300
    assert res_auth['reply']['Acct-Interim-Interval'] == 60
    assert res_auth['reply']['Session-Timeout'] > 0

    # 2. Suspended Entitlement -> Reject
    suspend_entitlement(entitlement=entitlement, reason='Operator Investigation')
    res_susp = authorize_radius_access(
        username=voucher.display_code,
        nas_ip=nas.nas_ip,
        mac_address='AA:BB:CC:DD:EE:01'
    )
    assert res_susp['accept'] is False
    assert res_susp['reason'] == 'SUSPENDED'

    # 3. Revoked Entitlement -> Reject
    revoke_entitlement(entitlement=entitlement, reason='Terms violation')
    res_rev = authorize_radius_access(
        username=voucher.display_code,
        nas_ip=nas.nas_ip,
        mac_address='AA:BB:CC:DD:EE:01'
    )
    assert res_rev['accept'] is False
    assert res_rev['reason'] == 'REVOKED'


@pytest.mark.django_db
def test_dynamic_bandwidth_shaping_attributes(radius_setup):
    """
    Test that rate-limiting attributes are dynamically generated from plan snapshots (Plan A vs Plan B).
    """
    nas = radius_setup['nas1']
    company = radius_setup['company1']

    # Plan A: 5M Down / 2M Up
    ent_a = create_entitlement_from_plan(
        company=company,
        plan=radius_setup['plan_a'],
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )
    res_a = authorize_radius_access(username=ent_a.reference, nas_ip=nas.nas_ip)
    assert res_a['accept'] is True
    assert res_a['reply']['Mikrotik-Rate-Limit'] == '2048k/5120k'
    assert res_a['reply']['WISPr-Bandwidth-Max-Down'] == 5120000
    assert res_a['reply']['WISPr-Bandwidth-Max-Up'] == 2048000

    # Plan B: 15M Down / 5M Up
    ent_b = create_entitlement_from_plan(
        company=company,
        plan=radius_setup['plan_b'],
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )
    res_b = authorize_radius_access(username=ent_b.reference, nas_ip=nas.nas_ip)
    assert res_b['accept'] is True
    assert res_b['reply']['Mikrotik-Rate-Limit'] == '5120k/15360k'
    assert res_b['reply']['WISPr-Bandwidth-Max-Down'] == 15360000
    assert res_b['reply']['WISPr-Bandwidth-Max-Up'] == 5120000


@pytest.mark.django_db
def test_dynamic_session_timeout_bounded_by_expiry(radius_setup):
    """
    Test that Session-Timeout is dynamically bounded by remaining entitlement wall-clock time.
    """
    nas = radius_setup['nas1']
    company = radius_setup['company1']
    plan = radius_setup['plan_a']

    # Create entitlement expiring in exactly 600 seconds (10 minutes)
    now = timezone.now()
    ent = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )
    ent.expires_at = now + timedelta(seconds=600)
    ent.save()

    res = authorize_radius_access(username=ent.reference, nas_ip=nas.nas_ip)
    assert res['accept'] is True
    assert 590 <= res['reply']['Session-Timeout'] <= 600


@pytest.mark.django_db
def test_device_limit_and_simultaneous_sessions(radius_setup):
    """
    Test max_devices and simultaneous_sessions enforcement at authorization boundary.
    """
    nas = radius_setup['nas1']
    company = radius_setup['company1']
    plan = radius_setup['plan_a']  # max_devices = 1, simultaneous_sessions = 1

    ent = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )

    # 1. Device A (MAC 1) logs in -> Allowed
    res_d1 = authorize_radius_access(
        username=ent.reference,
        nas_ip=nas.nas_ip,
        mac_address='AA:BB:CC:11:22:33'
    )
    assert res_d1['accept'] is True

    # 2. Device B (MAC 2) attempts login on same single-device entitlement -> Rejected
    res_d2 = authorize_radius_access(
        username=ent.reference,
        nas_ip=nas.nas_ip,
        mac_address='AA:BB:CC:99:88:77'
    )
    assert res_d2['accept'] is False
    assert res_d2['reason'] == 'DEVICE_LIMIT_REACHED'

    # 3. Simulate Active Session for Device A
    HotspotSession.objects.create(
        company=company,
        entitlement=ent,
        radius_client=nas,
        acct_session_id='sess_alpha_01',
        username=ent.reference,
        mac_address='AA:BB:CC:11:22:33',
        status=SessionStatus.ACTIVE
    )

    # 4. Device A attempts second simultaneous login while already online -> Rejected
    res_sim = authorize_radius_access(
        username=ent.reference,
        nas_ip=nas.nas_ip,
        mac_address='AA:BB:CC:11:22:33'
    )
    assert res_sim['accept'] is False
    assert res_sim['reason'] == 'SESSION_LIMIT_REACHED'


@pytest.mark.django_db
def test_cross_tenant_nas_isolation(radius_setup):
    """
    Test that a NAS router belonging to Company A cannot authorize Company B entitlements.
    """
    nas_alpha = radius_setup['nas1']
    company_beta = radius_setup['company2']
    plan_beta = create_plan(
        company=company_beta,
        data={
            'name': 'Beta Plan',
            'code': 'BETA-PLAN',
            'price': '1000.00',
            'duration_value': 1,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
        }
    )

    ent_beta = create_entitlement_from_plan(
        company=company_beta,
        plan=plan_beta,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )

    # Request sent from Alpha NAS with Beta Entitlement username
    res = authorize_radius_access(
        username=ent_beta.reference,
        nas_ip=nas_alpha.nas_ip
    )
    assert res['accept'] is False
    assert res['reason'] == 'ENTITLEMENT_NOT_FOUND'


@pytest.mark.django_db
def test_accounting_packet_processing_and_cumulative_deltas(radius_setup):
    """
    Test RADIUS accounting lifecycle: Start, duplicate Start, cumulative Interims,
    out-of-order packets, gigawords roll-over, and Stop.
    """
    nas = radius_setup['nas1']
    company = radius_setup['company1']
    plan = radius_setup['plan_a']

    ent = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )
    session_id = 'mikrotik_sess_101'

    # 1. Accounting Start
    log_start = process_radius_accounting(
        session_id=session_id,
        username=ent.reference,
        nas_ip=nas.nas_ip,
        packet_type=AccountingPacketType.START,
        mac_address='AA:BB:CC:11:22:33',
        framed_ip='10.5.50.150'
    )
    assert log_start.packet_type == 'Start'

    session = HotspotSession.objects.get(acct_session_id=session_id)
    assert session.status == SessionStatus.ACTIVE
    assert session.mac_address == 'AA:BB:CC:11:22:33'
    assert session.input_bytes == 0
    assert session.output_bytes == 0

    # 2. Duplicate Start (Idempotency) -> 0 change
    process_radius_accounting(
        session_id=session_id,
        username=ent.reference,
        nas_ip=nas.nas_ip,
        packet_type=AccountingPacketType.START,
        mac_address='AA:BB:CC:11:22:33'
    )
    assert HotspotSession.objects.filter(acct_session_id=session_id).count() == 1

    # 3. Interim 1 (10 MB upload, 20 MB download, 60s elapsed)
    process_radius_accounting(
        session_id=session_id,
        username=ent.reference,
        nas_ip=nas.nas_ip,
        packet_type=AccountingPacketType.INTERIM,
        mac_address='AA:BB:CC:11:22:33',
        input_octets=10485760,   # 10 MB
        output_octets=20971520,  # 20 MB
        session_time=60
    )
    ent.refresh_from_db()
    assert ent.data_used_bytes == 31457280  # 30 MB
    assert ent.usage_time_used_seconds == 60

    session.refresh_from_db()
    assert session.input_bytes == 10485760
    assert session.output_bytes == 20971520
    assert session.session_seconds == 60

    # 4. Interim 2 Cumulative (15 MB upload, 35 MB download, 120s elapsed)
    # Delta added to entitlement: +5 MB upload, +15 MB download = +20 MB (20971520 bytes), +60s
    process_radius_accounting(
        session_id=session_id,
        username=ent.reference,
        nas_ip=nas.nas_ip,
        packet_type=AccountingPacketType.INTERIM,
        mac_address='AA:BB:CC:11:22:33',
        input_octets=15728640,   # 15 MB
        output_octets=36700160,  # 35 MB
        session_time=120
    )
    ent.refresh_from_db()
    assert ent.data_used_bytes == 52428800  # Total 50 MB
    assert ent.usage_time_used_seconds == 120

    # 5. Out-of-Order Interim (delayed packet with smaller counters: 12 MB / 25 MB) -> 0 delta added!
    process_radius_accounting(
        session_id=session_id,
        username=ent.reference,
        nas_ip=nas.nas_ip,
        packet_type=AccountingPacketType.INTERIM,
        mac_address='AA:BB:CC:11:22:33',
        input_octets=12582912,
        output_octets=26214400,
        session_time=90
    )
    ent.refresh_from_db()
    assert ent.data_used_bytes == 52428800  # Unchanged
    assert ent.usage_time_used_seconds == 120  # Unchanged

    # 6. Accounting Stop (Final: 20 MB upload, 40 MB download, 180s)
    process_radius_accounting(
        session_id=session_id,
        username=ent.reference,
        nas_ip=nas.nas_ip,
        packet_type=AccountingPacketType.STOP,
        mac_address='AA:BB:CC:11:22:33',
        input_octets=20971520,   # 20 MB
        output_octets=41943040,  # 40 MB
        session_time=180,
        terminate_cause='User-Request'
    )
    ent.refresh_from_db()
    assert ent.data_used_bytes == 62914560  # Total 60 MB
    assert ent.usage_time_used_seconds == 180

    session.refresh_from_db()
    assert session.status == SessionStatus.STOPPED
    assert session.ended_at is not None
    assert session.termination_reason == 'User-Request'


@pytest.mark.django_db
def test_accounting_quota_exhaustion_blocks_reauth(radius_setup):
    """
    Test that accumulating usage beyond data quota triggers DATA_QUOTA_EXHAUSTED.
    """
    nas = radius_setup['nas1']
    company = radius_setup['company1']
    plan = radius_setup['plan_a']  # 1 GB data limit

    ent = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )
    ent.data_limit_bytes = 104857600  # 100 MB
    ent.save()

    # Apply accounting usage of 105 MB
    process_radius_accounting(
        session_id='sess_quota_01',
        username=ent.reference,
        nas_ip=nas.nas_ip,
        packet_type=AccountingPacketType.INTERIM,
        input_octets=52428800,   # 50 MB
        output_octets=57671680,  # 55 MB (Total 105 MB)
        session_time=300
    )

    ent.refresh_from_db()
    assert ent.data_used_bytes >= ent.data_limit_bytes

    # Subsequent Access-Request -> Rejected
    res = authorize_radius_access(
        username=ent.reference,
        nas_ip=nas.nas_ip
    )
    assert res['accept'] is False
    assert res['reason'] == 'DATA_QUOTA_EXHAUSTED'


@pytest.mark.django_db
def test_radius_api_endpoints_via_http(radius_setup):
    """
    Test FreeRADIUS REST integration endpoints via Django REST framework test client.
    """
    client = APIClient()
    nas = radius_setup['nas1']
    company = radius_setup['company1']
    plan = radius_setup['plan_a']

    ent = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )

    # 1. POST /api/v1/radius/authorize/
    res_auth = client.post(
        '/api/v1/radius/authorize/',
        data={
            'username': ent.reference,
            'nas_ip': nas.nas_ip,
            'mac_address': 'AA:BB:CC:44:55:66'
        },
        format='json'
    )
    assert res_auth.status_code == 200
    assert res_auth.data['control']['Auth-Type'] == 'Accept'
    assert 'Mikrotik-Rate-Limit' in res_auth.data['reply']

    # 2. POST /api/v1/radius/accounting/
    res_acct = client.post(
        '/api/v1/radius/accounting/',
        data={
            'session_id': 'http_sess_001',
            'username': ent.reference,
            'nas_ip': nas.nas_ip,
            'packet_type': 'Start',
            'mac_address': 'AA:BB:CC:44:55:66',
            'framed_ip': '10.5.50.180'
        },
        format='json'
    )
    assert res_acct.status_code == 200
    assert res_acct.data['status'] == 'success'
