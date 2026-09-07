import pytest
from unittest.mock import MagicMock, patch

from django.utils import timezone

from apps.companies.models import Company, RouterUplinkProfile
from apps.locations.models import Location
from apps.routers.models import Router, RouterHealthStatus
from apps.routers.services.router_client import RouterOSAPIClient, RouterOSError
from apps.routers.services.router_service import (
    collect_router_telemetry,
    set_router_credentials,
    test_router_connection as run_test_router_connection,
)


class MockHealthyRouterOSClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def query(self, cmd, args=None):
        if cmd == '/system/identity/print':
            return [{'name': 'MikroTik-Lab-Gateway'}]
        elif cmd == '/system/resource/print':
            return [{
                'version': '7.15.2 (stable)',
                'board-name': 'hAP ac lite',
                'architecture-name': 'mipsbe',
                'cpu-load': '12',
                'uptime': '3d04h12m',
                'free-memory': '29360128',
                'total-memory': '67108864',
            }]
        return []

    def execute(self, cmd, args=None):
        return True, 'OK'


class MockFailingRouterOSClient:
    def __init__(self, code='CONNECTION_TIMEOUT', message='Timed out connecting to 10.5.50.1:8728'):
        self.code = code
        self.message = message

    def __enter__(self):
        raise RouterOSError(code=self.code, message=self.message)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def router_setup(db):
    company = Company.objects.create(name="Router Test Co", slug="router-test-co")
    location = Location.objects.create(company=company, name="Main Office", code="MAIN-01")
    router = Router.objects.create(
        company=company,
        location=location,
        name="Main-GW",
        management_ip="10.5.50.1",
        api_port=8728,
        api_username="admin",
    )
    return {'company': company, 'location': location, 'router': router}


@pytest.mark.django_db
def test_router_credentials_encryption_and_property(router_setup):
    router = router_setup['router']
    assert router.has_credentials is False
    assert router.api_password == ''

    # Set password
    router.api_password = "SuperSecretPassword2026!"
    router.save()

    # Verify at rest
    router.refresh_from_db()
    assert router.api_password_encrypted != "SuperSecretPassword2026!"
    assert router.api_password == "SuperSecretPassword2026!"
    assert router.has_credentials is True


@pytest.mark.django_db
def test_routeros_client_requires_credentials_before_connecting(router_setup):
    router = router_setup['router']
    router.api_password_encrypted = ''
    router.save()

    # Attempting to build client for uncredentialed router should raise immediately
    with pytest.raises(RouterOSError) as exc_info:
        RouterOSAPIClient.for_router(router)

    assert exc_info.value.code == 'ROUTER_CREDENTIALS_NOT_CONFIGURED'
    assert 'does not have management credentials configured' in str(exc_info.value)


@pytest.mark.django_db
def test_test_router_connection_healthy(router_setup):
    router = router_setup['router']
    set_router_credentials(router, username="admin", password="password123")

    diag = run_test_router_connection(router, client_factory=lambda: MockHealthyRouterOSClient())
    assert diag['success'] is True
    assert diag['code'] == 'CONNECTED'
    assert diag['identity'] == 'MikroTik-Lab-Gateway'
    assert diag['routeros_version'] == '7.15.2 (stable)'
    assert diag['model'] == 'hAP ac lite'
    assert diag['cpu_load'] == 12
    assert diag['latency_ms'] is not None


@pytest.mark.django_db
def test_test_router_connection_unreachable(router_setup):
    router = router_setup['router']
    set_router_credentials(router, username="admin", password="password123")

    diag = run_test_router_connection(
        router,
        client_factory=lambda: MockFailingRouterOSClient(code='CONNECTION_TIMEOUT', message='Timeout after 4.0s')
    )
    assert diag['success'] is False
    assert diag['code'] == 'CONNECTION_TIMEOUT'
    assert 'Timeout after 4.0s' in diag['message']


@pytest.mark.django_db
def test_collect_router_telemetry_updates_healthy_state(router_setup):
    router = router_setup['router']
    set_router_credentials(router, username="admin", password="password123")

    diag = collect_router_telemetry(router, client_factory=lambda: MockHealthyRouterOSClient())
    assert diag['success'] is True

    router.refresh_from_db()
    assert router.health_status == RouterHealthStatus.ONLINE
    assert router.identity == 'MikroTik-Lab-Gateway'
    assert router.routeros_version == '7.15.2 (stable)'
    assert router.model == 'hAP ac lite'
    assert router.last_seen_at is not None
    assert router.last_health_check_at is not None
    assert router.system_resources.get('cpu_load') == 12


@pytest.mark.django_db
def test_collect_router_telemetry_failure_state(router_setup):
    router = router_setup['router']
    set_router_credentials(router, username="admin", password="password123")

    diag = collect_router_telemetry(
        router,
        client_factory=lambda: MockFailingRouterOSClient(code='AUTHENTICATION_FAILED', message='Bad user or pass')
    )
    assert diag['success'] is False

    router.refresh_from_db()
    assert router.health_status == RouterHealthStatus.DEGRADED
    assert 'Bad user or pass' in router.health_message
    assert router.system_resources.get('last_error', {}).get('code') == 'AUTHENTICATION_FAILED'


@pytest.mark.django_db
def test_router_uplink_profile_encrypted_password(router_setup):
    company = router_setup['company']
    router = router_setup['router']

    profile = RouterUplinkProfile.objects.create(
        company=company,
        router=router,
        name="Branch Airtel",
        ssid="Airtel-Branch-5G",
        password="MySecretWifiKey!",
        is_active=True
    )

    profile.refresh_from_db()
    assert profile.password_encrypted != "MySecretWifiKey!"
    assert profile.password == "MySecretWifiKey!"
    assert profile.has_password is True
