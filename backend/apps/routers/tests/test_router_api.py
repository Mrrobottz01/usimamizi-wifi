import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import Company, CompanyMembership
from apps.locations.models import Location
from apps.routers.models import Router, RouterHealthStatus
from .test_router_services import MockHealthyRouterOSClient, MockFailingRouterOSClient


@pytest.fixture
def api_setup(db):
    company = Company.objects.create(name="Router API Co", slug="router-api-co")
    location = Location.objects.create(company=company, name="Downtown Branch", code="DT-01")
    user = User.objects.create_user(email="netadmin@example.com", password="password123")
    CompanyMembership.objects.create(company=company, user=user, is_active=True)

    router = Router.objects.create(
        company=company,
        location=location,
        name="DT-Main-Router",
        management_ip="192.168.10.1",
        api_port=8728,
        api_username="admin",
    )
    router.api_password = "ExistingSecretPassword"
    router.save()

    return {'company': company, 'location': location, 'user': user, 'router': router}


@pytest.mark.django_db
def test_router_list_and_detail(api_setup):
    client = APIClient()
    client.force_authenticate(user=api_setup['user'])

    # List routers
    resp = client.get(f"/api/v1/routers/?company_id={api_setup['company'].id}")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    r_data = resp.data[0]
    assert r_data['name'] == 'DT-Main-Router'
    assert r_data['has_credentials'] is True
    assert 'api_password' not in r_data
    assert 'api_password_encrypted' not in r_data

    # Detail view
    detail_resp = client.get(f"/api/v1/routers/{api_setup['router'].id}/")
    assert detail_resp.status_code == 200
    assert detail_resp.data['id'] == str(api_setup['router'].id)


@pytest.mark.django_db
def test_router_create_and_credentials_rotation(api_setup):
    client = APIClient()
    client.force_authenticate(user=api_setup['user'])

    # Create a new router
    create_payload = {
        'location': str(api_setup['location'].id),
        'name': 'Branch-Router-02',
        'management_ip': '192.168.20.1',
        'api_port': 8728,
        'api_username': 'operator',
        'api_password': 'InitialPassword123',
    }
    create_resp = client.post(
        f"/api/v1/routers/?company_id={api_setup['company'].id}",
        create_payload,
        format='json'
    )
    assert create_resp.status_code == 201
    new_id = create_resp.data['id']
    new_router = Router.objects.get(id=new_id)
    assert new_router.has_credentials is True
    assert new_router.api_password == 'InitialPassword123'
    assert 'api_password' not in create_resp.data

    # Rotate credentials
    cred_payload = {
        'api_username': 'superadmin',
        'api_password': 'RotatedPassword456!',
        'api_port': 8729,
        'use_tls': True,
    }
    cred_resp = client.post(
        f"/api/v1/routers/{new_id}/credentials/",
        cred_payload,
        format='json'
    )
    assert cred_resp.status_code == 200
    new_router.refresh_from_db()
    assert new_router.api_username == 'superadmin'
    assert new_router.api_password == 'RotatedPassword456!'
    assert new_router.api_port == 8729
    assert new_router.use_tls is True


@pytest.mark.django_db
def test_router_health_and_refresh_views(api_setup, monkeypatch):
    client = APIClient()
    client.force_authenticate(user=api_setup['user'])
    router = api_setup['router']

    # Read initial health
    health_resp = client.get(f"/api/v1/routers/{router.id}/health/")
    assert health_resp.status_code == 200
    assert health_resp.data['health_status'] == RouterHealthStatus.UNKNOWN
    assert health_resp.data['has_credentials'] is True

    # Mock test connection
    monkeypatch.setattr(
        'apps.routers.api.views.test_router_connection',
        lambda r, timeout=4.0: {
            'success': True,
            'code': 'CONNECTED',
            'message': 'Connected OK',
            'latency_ms': 12.5,
            'identity': 'MockGW',
            'routeros_version': '7.15',
            'model': 'hAP',
        }
    )

    test_resp = client.post(f"/api/v1/routers/{router.id}/test-connection/")
    assert test_resp.status_code == 200
    assert test_resp.data['code'] == 'CONNECTED'
    assert test_resp.data['latency_ms'] == 12.5

    # Mock refresh telemetry
    monkeypatch.setattr(
        'apps.routers.api.views.collect_router_telemetry',
        lambda r, timeout=4.0: {
            'success': True,
            'code': 'CONNECTED',
            'message': 'Telemetry refreshed',
        }
    )

    refresh_resp = client.post(f"/api/v1/routers/{router.id}/refresh-health/")
    assert refresh_resp.status_code == 200
    assert refresh_resp.data['diag']['success'] is True
