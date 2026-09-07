import socket
from datetime import timedelta
from unittest.mock import MagicMock, patch
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.companies.models import Company, CompanyStatus
from apps.core.models import IncidentStatus, ServiceIncident, ServiceName, SystemWatchdogConfig
from apps.core.services.watchdog_services import (
    ProbeResult,
    evaluate_and_alert_service,
    probe_database,
    probe_freeradius,
    probe_router,
    run_full_watchdog_cycle,
    send_system_alert_sms,
)
from apps.locations.models import Location
from apps.notifications.models import NotificationMessage, NotificationProviderConfiguration, SMSProviderType
from apps.routers.models import Router, RouterHealthStatus


@pytest.fixture
def setup_company(db):
    company = Company.objects.create(
        name="Usimamizi Test Telecom",
        slug="usimamizi-test",
        status=CompanyStatus.ACTIVE
    )
    # Ensure a mock SMS provider is available for test SMS
    NotificationProviderConfiguration.objects.get_or_create(
        code="mock-test-sms",
        defaults={
            "name": "Mock Test Provider",
            "provider_type": SMSProviderType.MOCK,
            "channel": "SMS",
            "is_active": True,
            "priority": 1,
        }
    )
    return company


@pytest.mark.django_db
def test_freeradius_probe_down():
    """Verify probe_freeradius detects an inactive or closed port as DOWN."""
    # Port 19999 is unlikely to be listening
    res = probe_freeradius(host='127.0.0.1', port=19999, timeout=0.2)
    assert res.service_name == ServiceName.FREERADIUS
    assert res.is_healthy is False
    assert res.status == IncidentStatus.DOWN
    assert "127.0.0.1:19999" in res.service_identifier


@pytest.mark.django_db
def test_freeradius_probe_healthy_mock():
    """Verify probe_freeradius detects valid RADIUS Access-Reject (Code 3) as HEALTHY."""
    mock_sock = MagicMock()
    # 20-byte RADIUS header with Code=3 (Access-Reject), ID=1, Length=20, 16-byte authenticator
    mock_radius_response = bytes([3, 1, 0, 20]) + b"\x00" * 16
    mock_sock.recvfrom.return_value = (mock_radius_response, ('127.0.0.1', 1812))

    with patch('socket.socket', return_value=mock_sock):
        res = probe_freeradius(host='127.0.0.1', port=1812, timeout=1.0)
        assert res.is_healthy is True
        assert res.status == IncidentStatus.HEALTHY
        assert res.extra_data.get('response_code') == 3
        assert res.extra_data.get('response_type') == 'Access-Reject'


@pytest.mark.django_db
def test_database_probe():
    """Verify probe_database executes successfully on active DB."""
    res = probe_database()
    assert res.service_name == ServiceName.DATABASE
    assert res.is_healthy is True
    assert res.status == IncidentStatus.HEALTHY
    assert res.latency_ms >= 0


@pytest.mark.django_db
def test_router_probe(setup_company):
    """Verify router probe handles unreachable router cleanly and updates status."""
    location = Location.objects.create(
        company=setup_company,
        name="HQ Test Location",
        code="LOC-HQ-001"
    )
    router = Router.objects.create(
        company=setup_company,
        location=location,
        name="Test Edge Gateway",
        management_ip="192.0.2.1",  # Test network RFC 5737
        api_port=8728,
        is_active=True
    )

    res = probe_router(router, timeout=0.2)
    assert res.service_name == ServiceName.ROUTER_GATEWAY
    assert res.is_healthy is False
    assert res.status == IncidentStatus.DOWN

    router.refresh_from_db()
    assert router.health_status == RouterHealthStatus.OFFLINE
    assert router.last_health_check_at is not None
    assert "unreachable" in router.health_message.lower()


@pytest.mark.django_db
def test_incident_lifecycle_and_sms_alerts(setup_company):
    """
    End-to-end incident lifecycle test:
    1. Service failure creates ServiceIncident and dispatches alert SMS.
    2. Repeated check during cooldown suppresses repeat SMS.
    3. Expiration of cooldown allows repeat SMS.
    4. Recovery marks incident resolved and sends recovery SMS.
    """
    config = SystemWatchdogConfig.objects.create(
        company=setup_company,
        is_enabled=True,
        alert_phone_numbers="+255712345678",
        alert_cooldown_minutes=30,
        notify_on_recovery=True
    )

    down_probe = ProbeResult(
        service_name=ServiceName.FREERADIUS,
        service_identifier="127.0.0.1:1812",
        status=IncidentStatus.DOWN,
        is_healthy=False,
        error_message="Daemon terminated unexpectedly"
    )

    # 1. First probe failure: should create incident & send initial SMS alert
    incident = evaluate_and_alert_service(down_probe, config=config, company=setup_company, send_alerts=True)
    assert incident is not None
    assert incident.service_name == ServiceName.FREERADIUS
    assert incident.status == IncidentStatus.DOWN
    assert incident.alert_count == 1
    assert incident.alert_sent_at is not None
    assert incident.resolved_at is None

    # Verify SMS was created and dispatched
    sms_count = NotificationMessage.objects.filter(recipient="+255712345678").count()
    assert sms_count == 1

    # 2. Second probe failure immediately: within cooldown, so SMS should NOT be resent
    incident_2 = evaluate_and_alert_service(down_probe, config=config, company=setup_company, send_alerts=True)
    assert incident_2.id == incident.id
    assert incident_2.alert_count == 1  # Still 1, suppressed by cooldown
    assert NotificationMessage.objects.filter(recipient="+255712345678").count() == 1

    # 3. Simulate passage of time past 30m cooldown
    incident_2.alert_sent_at = timezone.now() - timedelta(minutes=31)
    incident_2.save()

    incident_3 = evaluate_and_alert_service(down_probe, config=config, company=setup_company, send_alerts=True)
    assert incident_3.alert_count == 2  # Repeat alert dispatched!
    assert NotificationMessage.objects.filter(recipient="+255712345678").count() == 2

    # 4. Service recovers: HEALTHY probe
    healthy_probe = ProbeResult(
        service_name=ServiceName.FREERADIUS,
        service_identifier="127.0.0.1:1812",
        status=IncidentStatus.HEALTHY,
        is_healthy=True,
        latency_ms=1.2
    )

    resolved_incident = evaluate_and_alert_service(healthy_probe, config=config, company=setup_company, send_alerts=True)
    assert resolved_incident is not None
    assert resolved_incident.id == incident.id
    assert resolved_incident.status == IncidentStatus.HEALTHY
    assert resolved_incident.resolved_at is not None
    assert resolved_incident.recovery_alert_sent_at is not None

    # Verify recovery SMS was dispatched
    assert NotificationMessage.objects.filter(recipient="+255712345678").count() == 3


@pytest.mark.django_db
def test_watchdog_api_status_view(setup_company):
    """Verify GET /api/v1/health/watchdog/ returns complete status payload."""
    client = APIClient()
    response = client.get('/api/v1/health/watchdog/')
    assert response.status_code == 200
    data = response.data
    assert 'timestamp' in data
    assert 'overall_status' in data
    assert 'probes' in data
    assert 'active_incidents' in data
    assert 'recent_resolved' in data
    assert 'config' in data


@pytest.mark.django_db
def test_watchdog_api_config_and_test_sms(setup_company):
    """Verify watchdog config updates and test SMS trigger."""
    client = APIClient()

    # GET config
    res = client.get('/api/v1/health/watchdog/config/')
    assert res.status_code == 200

    # PUT config
    update_res = client.put('/api/v1/health/watchdog/config/', {
        'alert_phone_numbers': '+255712999888,+255788111222',
        'alert_cooldown_minutes': 45,
        'notify_on_recovery': True
    }, format='json')
    assert update_res.status_code == 200
    assert update_res.data['config']['alert_phone_numbers'] == '+255712999888,+255788111222'
    assert update_res.data['config']['alert_cooldown_minutes'] == 45

    # POST test SMS
    sms_res = client.post('/api/v1/health/watchdog/test-sms/', {
        'phone_number': '+255712999888'
    }, format='json')
    assert sms_res.status_code == 200
    assert sms_res.data['status'] == 'dispatched'
    assert sms_res.data['recipients_contacted'] == 1
