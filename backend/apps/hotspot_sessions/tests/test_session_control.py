import hashlib
import struct
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.services.company_services import create_company
from apps.entitlements.models import EntitlementStatus
from apps.entitlements.services.entitlement_services import (
    grant_manual_entitlement,
    revoke_entitlement,
    suspend_entitlement,
)
from apps.hotspot_sessions.models import (
    DisconnectStatus,
    HotspotSession,
    SessionDisconnectRequest,
    SessionDisconnectTrigger,
    SessionStatus,
)
from apps.hotspot_sessions.services.session_control import (
    RADIUS_CODE_DISCONNECT_ACK,
    RADIUS_CODE_DISCONNECT_NAK,
    build_disconnect_packet,
    disconnect_hotspot_session,
    reconcile_stale_sessions,
    release_entitlement_device,
    send_radius_disconnect_packet,
)
from apps.hotspot_sessions.services.session_services import (
    get_active_sessions_count_for_entitlement,
)
from apps.plans.models import DurationUnit, ValidityMode
from apps.plans.services.plan_services import create_plan
from apps.radius.models import EntitlementDevice, RadiusClient
from apps.radius.services.radius_services import normalize_mac_address


@pytest.fixture
def session_control_setup():
    user = User.objects.create_user(email='operator@sessionlab.co.tz', password='Password123!')
    company = create_company(name='Session Lab Co', user=user)

    plan = create_plan(
        company=company,
        data={
            'name': 'Session Test Plan',
            'code': 'SESS-1H',
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

    entitlement = grant_manual_entitlement(
        company=company,
        plan=plan,
        actor=user,
        reason='Session Testing'
    )
    entitlement.status = EntitlementStatus.ACTIVE
    entitlement.save()

    nas = RadiusClient.objects.create(
        company=company,
        name='Lab MikroTik Router',
        nas_ip='192.168.88.1',
        nas_identifier='lab_hap_ac_lite',
        is_active=True
    )
    nas.shared_secret = 'radius_shared_secret_lab'
    nas.save()

    session = HotspotSession.objects.create(
        company=company,
        entitlement=entitlement,
        radius_client=nas,
        acct_session_id='sess_1001',
        username='TEST-VOUCHER-01',
        mac_address='AA:BB:CC:DD:EE:11',
        ip_address='10.5.50.100',
        status=SessionStatus.ACTIVE,
        started_at=timezone.now(),
        last_accounting_at=timezone.now()
    )

    return {
        'user': user,
        'company': company,
        'plan': plan,
        'entitlement': entitlement,
        'nas': nas,
        'session': session
    }


def _make_mock_radius_response(code: int, identifier: int, req_auth: bytes, secret: str) -> bytes:
    """Generate mock RFC 3576 RADIUS response with verified Authenticator."""
    length = 20
    header_no_auth = struct.pack('!BBH', code, identifier, length)
    resp_auth = hashlib.md5(header_no_auth + req_auth + secret.encode('utf-8')).digest()
    return header_no_auth + resp_auth


@pytest.mark.django_db
def test_build_disconnect_packet():
    packet, req_auth = build_disconnect_packet(
        identifier=10,
        secret='radius_shared_secret_lab',
        username='TEST-USER',
        acct_session_id='sess_8921',
        nas_ip='192.168.88.1',
        calling_station_id='AA:BB:CC:DD:EE:FF'
    )
    assert len(packet) >= 20
    code, identifier, length = struct.unpack('!BBH', packet[:4])
    assert code == 40
    assert identifier == 10
    assert len(req_auth) == 16


@pytest.mark.django_db
@patch('socket.socket')
def test_send_radius_disconnect_packet_ack(mock_socket_class):
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock

    secret = 'radius_shared_secret_lab'

    def fake_recvfrom(bufsize):
        # Read the sent packet from sendto to extract ID and Request Authenticator
        sent_packet = mock_sock.sendto.call_args[0][0]
        code, ident, length = struct.unpack('!BBH', sent_packet[:4])
        req_auth = sent_packet[4:20]
        resp_data = _make_mock_radius_response(RADIUS_CODE_DISCONNECT_ACK, ident, req_auth, secret)
        return (resp_data, ('192.168.88.1', 3799))

    mock_sock.recvfrom.side_effect = fake_recvfrom

    res = send_radius_disconnect_packet(
        nas_ip='192.168.88.1',
        secret=secret,
        username='TEST-VOUCHER',
        acct_session_id='sess_101',
    )
    assert res['success'] is True
    assert res['status'] == DisconnectStatus.ACKNOWLEDGED
    assert res['response_code'] == 'Disconnect-ACK'


@pytest.mark.django_db
@patch('socket.socket')
def test_send_radius_disconnect_packet_nak(mock_socket_class):
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock

    secret = 'radius_shared_secret_lab'

    def fake_recvfrom(bufsize):
        sent_packet = mock_sock.sendto.call_args[0][0]
        code, ident, length = struct.unpack('!BBH', sent_packet[:4])
        req_auth = sent_packet[4:20]
        resp_data = _make_mock_radius_response(RADIUS_CODE_DISCONNECT_NAK, ident, req_auth, secret)
        return (resp_data, ('192.168.88.1', 3799))

    mock_sock.recvfrom.side_effect = fake_recvfrom

    res = send_radius_disconnect_packet(
        nas_ip='192.168.88.1',
        secret=secret,
        username='TEST-VOUCHER',
        acct_session_id='sess_101',
    )
    assert res['success'] is False
    assert res['status'] == DisconnectStatus.FAILED
    assert res['response_code'] == 'Disconnect-NAK'


@pytest.mark.django_db
@patch('apps.hotspot_sessions.services.session_control.send_radius_disconnect_packet')
def test_disconnect_hotspot_session_lifecycle(mock_send, session_control_setup):
    setup = session_control_setup
    mock_send.return_value = {
        'success': True,
        'status': DisconnectStatus.ACKNOWLEDGED,
        'response_code': 'Disconnect-ACK',
        'response_message': 'OK',
        'attempts': 1
    }

    req = disconnect_hotspot_session(
        session=setup['session'],
        trigger_type=SessionDisconnectTrigger.MANUAL,
        reason='Customer requested disconnect',
        requested_by=setup['user']
    )

    assert req.status == DisconnectStatus.ACKNOWLEDGED
    assert req.acknowledged_at is not None
    # Crucial architectural rule: HotspotSession remains ACTIVE until Accounting Stop / reconciliation
    setup['session'].refresh_from_db()
    assert setup['session'].status == SessionStatus.ACTIVE


@pytest.mark.django_db
def test_disconnect_already_stopped_session(session_control_setup):
    setup = session_control_setup
    setup['session'].status = SessionStatus.STOPPED
    setup['session'].save()

    req = disconnect_hotspot_session(
        session=setup['session'],
        trigger_type=SessionDisconnectTrigger.MANUAL,
        reason='Test'
    )
    assert req.status == DisconnectStatus.CANCELLED
    assert req.response_code == 'ALREADY_STOPPED'


@pytest.mark.django_db
@patch('apps.hotspot_sessions.services.session_control.send_radius_disconnect_packet')
def test_entitlement_suspension_triggers_disconnect(mock_send, session_control_setup):
    setup = session_control_setup
    mock_send.return_value = {
        'success': True,
        'status': DisconnectStatus.ACKNOWLEDGED,
        'response_code': 'Disconnect-ACK',
        'response_message': 'OK',
        'attempts': 1
    }

    suspend_entitlement(
        entitlement=setup['entitlement'],
        actor=setup['user'],
        reason='Suspicious activity'
    )

    setup['entitlement'].refresh_from_db()
    assert setup['entitlement'].status == EntitlementStatus.SUSPENDED

    # Verify disconnect request was enqueued for the active session
    req = SessionDisconnectRequest.objects.filter(
        hotspot_session=setup['session'],
        trigger_type=SessionDisconnectTrigger.ENTITLEMENT_SUSPENDED
    ).first()
    assert req is not None
    assert req.status == DisconnectStatus.ACKNOWLEDGED


@pytest.mark.django_db
@patch('apps.hotspot_sessions.services.session_control.send_radius_disconnect_packet')
def test_entitlement_revocation_triggers_disconnect(mock_send, session_control_setup):
    setup = session_control_setup
    mock_send.return_value = {
        'success': True,
        'status': DisconnectStatus.ACKNOWLEDGED,
        'response_code': 'Disconnect-ACK',
        'response_message': 'OK',
        'attempts': 1
    }

    revoke_entitlement(
        entitlement=setup['entitlement'],
        actor=setup['user'],
        reason='Refund processed'
    )

    setup['entitlement'].refresh_from_db()
    assert setup['entitlement'].status == EntitlementStatus.REVOKED

    req = SessionDisconnectRequest.objects.filter(
        hotspot_session=setup['session'],
        trigger_type=SessionDisconnectTrigger.ENTITLEMENT_REVOKED
    ).first()
    assert req is not None
    assert req.status == DisconnectStatus.ACKNOWLEDGED


@pytest.mark.django_db
def test_stale_session_reconciliation_and_simultaneous_limit(session_control_setup):
    setup = session_control_setup
    session = setup['session']

    # Set last accounting to 10 minutes ago
    session.last_accounting_at = timezone.now() - timezone.timedelta(minutes=10)
    session.save()

    # Before reconciliation, simultaneous session calculation excludes the stale session
    active_count = get_active_sessions_count_for_entitlement(setup['entitlement'])
    assert active_count == 0

    # Run reconciliation task
    stale_count = reconcile_stale_sessions(company=setup['company'], stale_threshold_seconds=300)
    assert stale_count >= 1

    session.refresh_from_db()
    assert session.status == SessionStatus.STALE
    assert session.termination_reason == 'STALE_ACCOUNTING_TIMEOUT'


@pytest.mark.django_db
def test_release_entitlement_device_service(session_control_setup):
    setup = session_control_setup
    mac = 'AA:BB:CC:DD:EE:99'

    EntitlementDevice.objects.create(
        entitlement=setup['entitlement'],
        mac_address=normalize_mac_address(mac)
    )
    assert EntitlementDevice.objects.filter(entitlement=setup['entitlement']).count() == 1

    released = release_entitlement_device(
        entitlement=setup['entitlement'],
        mac_address=mac,
        company=setup['company'],
        user=setup['user'],
        reason='Customer replaced lost phone'
    )
    assert released is True
    assert EntitlementDevice.objects.filter(entitlement=setup['entitlement']).count() == 0


@pytest.mark.django_db
@patch('apps.hotspot_sessions.services.session_control.send_radius_disconnect_packet')
def test_session_disconnect_api_endpoints(mock_send, session_control_setup):
    setup = session_control_setup
    mock_send.return_value = {
        'success': True,
        'status': DisconnectStatus.ACKNOWLEDGED,
        'response_code': 'Disconnect-ACK',
        'response_message': 'OK',
        'attempts': 1
    }

    client = APIClient()
    client.force_authenticate(user=setup['user'])

    # 1. Manual Disconnect POST
    url = f"/api/v1/sessions/{setup['session'].id}/disconnect/?company_id={setup['company'].id}"
    resp = client.post(url, {'reason': 'Admin manual termination'}, format='json')
    assert resp.status_code == 200
    assert resp.data['status'] == DisconnectStatus.ACKNOWLEDGED

    # 2. Disconnect History GET
    history_url = f"/api/v1/sessions/{setup['session'].id}/disconnect-history/?company_id={setup['company'].id}"
    h_resp = client.get(history_url)
    assert h_resp.status_code == 200
    assert len(h_resp.data) == 1
    assert h_resp.data[0]['reason'] == 'Admin manual termination'
