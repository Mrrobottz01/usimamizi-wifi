import pytest
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.accounts.models import User
from apps.companies.models import Company, CompanyMembership, HotspotConfiguration
from apps.locations.models import Location
from apps.radius.models import RadiusClient
from apps.routers.models import Router, RouterHealthStatus
from apps.routers.services.provisioning_service import (
    generate_router_bootstrap_script,
    provision_router_via_api,
)
from apps.routers.tests.test_router_services import MockHealthyRouterOSClient


@pytest.fixture
def prov_setup(db):
    company = Company.objects.create(name="Provisioning Test Co", slug="prov-test-co")
    location = Location.objects.create(company=company, name="Safari Camp", code="SC-01")
    user = User.objects.create_user(email="admin@provtest.com", password="password123")
    CompanyMembership.objects.create(company=company, user=user, is_active=True)

    router = Router.objects.create(
        company=company,
        location=location,
        name="Safari-Gateway-01",
        management_ip="192.168.1.200",
        api_port=8728,
        api_username="admin",
    )
    router.api_password = "SecretPassword123"
    router.save()

    hotspot = HotspotConfiguration.objects.create(
        company=company,
        router=router,
        location=location,
        ssid="Safari-Camp-Guest",
        interface_name="bridgeHotspot",
        server_name="hotspot-safari",
        gateway_ip="10.10.10.1",
    )

    radius_client = RadiusClient.objects.create(
        company=company,
        router=router,
        name="Safari-Gateway-01",
        nas_ip="192.168.1.200",
        shared_secret="secret_shared_aaa_123",
    )

    return {
        'company': company,
        'location': location,
        'user': user,
        'router': router,
        'hotspot': hotspot,
        'radius_client': radius_client,
    }


@pytest.mark.django_db
def test_generate_router_bootstrap_script(prov_setup):
    router = prov_setup['router']
    hotspot = prov_setup['hotspot']

    script = generate_router_bootstrap_script(
        router=router,
        hotspot=hotspot,
        radius_server_ip="192.168.1.50",
        shared_secret="my_custom_secret",
        portal_base_url="https://wifi.safaricamp.tz",
    )

    assert "/system identity set name=\"Safari-Gateway-01\"" in script
    assert "/ip service set api disabled=no port=8728" in script
    assert "/radius incoming set accept=yes port=3799" in script
    assert "address=192.168.1.50" in script
    assert "secret=\"my_custom_secret\"" in script
    assert "use-radius=yes" in script
    assert "radius-accounting=yes" in script
    assert "radius-interim-update=60s" in script
    assert "api.snippe.sh" in script
    assert "wifi.safaricamp.tz" in script
    assert "new-ttl=set:1" in script
    assert "out-interface=bridgeHotspot" in script
    assert "ttl=equal:63" in script
    assert "ttl=equal:127" in script


@pytest.mark.django_db
def test_provision_router_via_api_mock(prov_setup):
    router = prov_setup['router']

    res = provision_router_via_api(
        router=router,
        client_factory=lambda: MockHealthyRouterOSClient(),
    )

    assert res['success'] is True
    assert res['router_name'] == "Safari-Gateway-01"
    assert len(res['steps']) >= 4
    step_names = [s['name'] for s in res['steps']]
    assert 'connectivity' in step_names
    assert 'api_service' in step_names
    assert 'radius_client' in step_names
    assert 'hotspot_profile' in step_names

    router.refresh_from_db()
    assert router.health_status == RouterHealthStatus.ONLINE
    assert 'provisioning' in router.system_resources
    assert router.system_resources['provisioning']['success'] is True


@pytest.mark.django_db
def test_router_provision_endpoints(prov_setup):
    client = APIClient()
    client.force_authenticate(user=prov_setup['user'])
    router = prov_setup['router']

    # 1. Test POST /provision/ with mocked RouterOS
    with patch('apps.routers.api.views.provision_router_via_api') as mock_prov:
        mock_prov.return_value = {
            'success': True,
            'router_id': str(router.id),
            'router_name': router.name,
            'management_ip': str(router.management_ip),
            'health_status': RouterHealthStatus.ONLINE,
            'elapsed_ms': 120.5,
            'steps': [{'name': 'connectivity', 'success': True, 'message': 'OK'}],
            'telemetry': {'success': True},
        }

        resp = client.post(f"/api/v1/routers/{router.id}/provision/", {})
        assert resp.status_code == 200
        assert resp.data['result']['success'] is True

    # 2. Test GET /bootstrap-script/
    resp_script = client.get(f"/api/v1/routers/{router.id}/bootstrap-script/")
    assert resp_script.status_code == 200
    assert 'command' in resp_script.data
    assert '/tool fetch' in resp_script.data['command']
    assert '/import' in resp_script.data['command']
    assert 'script' in resp_script.data
    assert 'Safari-Gateway-01' in resp_script.data['script']

    # 3. Test GET /bootstrap.rsc (Raw public endpoint)
    client.logout()
    raw_resp = client.get(f"/api/v1/routers/{router.id}/bootstrap.rsc")
    assert raw_resp.status_code == 200
    assert raw_resp['Content-Type'].startswith('text/plain')
    assert b"USIMAMIZI WI-FI" in raw_resp.content
