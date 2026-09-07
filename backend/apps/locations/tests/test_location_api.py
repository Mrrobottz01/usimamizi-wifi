import pytest
from decimal import Decimal
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import Company, CompanyMembership, HotspotConfiguration
from apps.locations.models import Location, LocationStatus, SiteType
from apps.routers.models import Router, RouterHealthStatus
from apps.hotspot_sessions.models import HotspotSession, SessionStatus


from apps.plans.models import Plan
from apps.entitlements.models import AccessEntitlement


@pytest.fixture
def location_api_setup(db):
    user_a = User.objects.create_user(email='admin@tenant-a.com', password='Password123!')
    company_a = Company.objects.create(name='Tenant A', slug='tenant-a')
    CompanyMembership.objects.create(company=company_a, user=user_a, is_active=True)

    loc1 = Location.objects.create(
        company=company_a,
        name='Kariakoo Branch',
        code='LOC-DAR-001',
        region='Dar es Salaam',
        district='Ilala',
        address='Lumumba Street',
        site_type=SiteType.BRANCH,
        status=LocationStatus.ACTIVE,
        contact_person='Juma Ally',
        contact_phone='+255712345678',
    )
    loc2 = Location.objects.create(
        company=company_a,
        name='Arusha Clocktower',
        code='LOC-ARU-001',
        region='Arusha',
        district='Arusha Urban',
        address='Clocktower Roundabout',
        site_type=SiteType.OFFICE,
        status=LocationStatus.ACTIVE,
    )

    router1 = Router.objects.create(
        company=company_a,
        location=loc1,
        name='Kariakoo Gateway',
        management_ip='10.5.50.1',
        health_status=RouterHealthStatus.ONLINE,
    )
    hotspot1 = HotspotConfiguration.objects.create(
        company=company_a,
        location=loc1,
        router=router1,
        name='Kariakoo Wi-Fi',
        slug='kariakoo-wifi',
        is_default=True,
    )
    plan = Plan.objects.create(
        company=company_a,
        name='Basic',
        code='BASIC-1',
        price=Decimal('1000.00'),
        duration_value=1,
        duration_unit='HOURS',
    )
    ent = AccessEntitlement.objects.create(
        company=company_a,
        plan=plan,
        source_type='MANUAL',
    )
    HotspotSession.objects.create(
        company=company_a,
        hotspot=hotspot1,
        entitlement=ent,
        acct_session_id='sess-loc-001',
        username='0712345678',
        mac_address='AA:BB:CC:DD:EE:01',
        ip_address='10.5.50.50',
        status=SessionStatus.ACTIVE,
    )

    # Tenant B (Isolation testing)
    user_b = User.objects.create_user(email='admin@tenant-b.com', password='Password123!')
    company_b = Company.objects.create(name='Tenant B', slug='tenant-b')
    CompanyMembership.objects.create(company=company_b, user=user_b, is_active=True)
    loc_b = Location.objects.create(
        company=company_b,
        name='Tenant B Site',
        code='LOC-TB-001',
        status=LocationStatus.ACTIVE,
    )

    return {
        'user_a': user_a,
        'company_a': company_a,
        'loc1': loc1,
        'loc2': loc2,
        'router1': router1,
        'hotspot1': hotspot1,
        'user_b': user_b,
        'company_b': company_b,
        'loc_b': loc_b,
    }


@pytest.mark.django_db
def test_location_list_and_metrics_aggregation(location_api_setup):
    client = APIClient()
    user = location_api_setup['user_a']
    client.force_authenticate(user=user)

    # 1. List locations
    resp = client.get('/api/v1/locations/')
    assert resp.status_code == 200
    assert len(resp.data) == 2

    # Find Kariakoo branch and check aggregations
    kariakoo = next(l for l in resp.data if l['code'] == 'LOC-DAR-001')
    assert kariakoo['router_count'] == 1
    assert kariakoo['online_router_count'] == 1
    assert kariakoo['hotspot_count'] == 1
    assert kariakoo['active_session_count'] == 1
    assert kariakoo['network_health'] == 'HEALTHY'


@pytest.mark.django_db
def test_location_search_and_filters(location_api_setup):
    client = APIClient()
    user = location_api_setup['user_a']
    client.force_authenticate(user=user)

    # Filter: region
    resp_region = client.get('/api/v1/locations/?region=Arusha')
    assert resp_region.status_code == 200
    assert len(resp_region.data) == 1
    assert resp_region.data[0]['name'] == 'Arusha Clocktower'

    # Filter: site_type
    resp_site = client.get('/api/v1/locations/?site_type=BRANCH')
    assert resp_site.status_code == 200
    assert len(resp_site.data) == 1
    assert resp_site.data[0]['code'] == 'LOC-DAR-001'

    # Search: contact person
    resp_search = client.get('/api/v1/locations/?search=Juma')
    assert resp_search.status_code == 200
    assert len(resp_search.data) == 1
    assert resp_search.data[0]['name'] == 'Kariakoo Branch'


@pytest.mark.django_db
def test_location_crud_lifecycle(location_api_setup):
    client = APIClient()
    user = location_api_setup['user_a']
    client.force_authenticate(user=user)

    # 1. Create Location
    resp_create = client.post('/api/v1/locations/', {
        'name': 'Mwanza Rock City Mall',
        'region': 'Mwanza',
        'district': 'Nyamagana',
        'site_type': 'MALL',
        'operating_hours': '08:00 - 22:00',
        'latitude': '-2.516667',
        'longitude': '32.900000',
        'timezone': 'Africa/Dar_es_Salaam',
    }, format='json')
    assert resp_create.status_code == 201
    loc_id = resp_create.data['id']
    assert resp_create.data['code'].startswith('LOC-MWA-')
    assert resp_create.data['site_type'] == 'MALL'

    # 2. Retrieve Location Detail
    resp_get = client.get(f'/api/v1/locations/{loc_id}/')
    assert resp_get.status_code == 200
    assert resp_get.data['name'] == 'Mwanza Rock City Mall'
    assert 'network_summary' in resp_get.data

    # 3. Patch Location
    resp_patch = client.patch(f'/api/v1/locations/{loc_id}/', {
        'contact_person': 'Baraka Mwita',
        'contact_phone': '+255768000111',
    }, format='json')
    assert resp_patch.status_code == 200
    assert resp_patch.data['contact_person'] == 'Baraka Mwita'

    # 4. Safe Delete: Unreferenced location -> deleted permanently
    resp_del = client.delete(f'/api/v1/locations/{loc_id}/')
    assert resp_del.status_code == 200
    assert resp_del.data['action'] == 'deleted'


@pytest.mark.django_db
def test_location_safe_delete_and_reactivate_in_use(location_api_setup):
    client = APIClient()
    user = location_api_setup['user_a']
    loc1 = location_api_setup['loc1']
    client.force_authenticate(user=user)

    # Attempt delete on location with active router/hotspot -> safe deactivation
    resp_del = client.delete(f'/api/v1/locations/{loc1.id}/')
    assert resp_del.status_code == 200
    assert resp_del.data['action'] == 'deactivated'

    loc1.refresh_from_db()
    assert loc1.is_active is False
    assert loc1.status == LocationStatus.INACTIVE

    # Reactivate endpoint
    resp_react = client.post(f'/api/v1/locations/{loc1.id}/reactivate/')
    assert resp_react.status_code == 200
    assert resp_react.data['action'] == 'reactivated'

    loc1.refresh_from_db()
    assert loc1.is_active is True
    assert loc1.status == LocationStatus.ACTIVE


@pytest.mark.django_db
def test_location_subresources_endpoints(location_api_setup):
    client = APIClient()
    user = location_api_setup['user_a']
    loc1 = location_api_setup['loc1']
    loc2 = location_api_setup['loc2']
    router1 = location_api_setup['router1']
    client.force_authenticate(user=user)

    # 1. GET /locations/{id}/routers/
    resp_routers = client.get(f'/api/v1/locations/{loc1.id}/routers/')
    assert resp_routers.status_code == 200
    assert len(resp_routers.data) == 1
    assert resp_routers.data[0]['name'] == 'Kariakoo Gateway'

    # 2. GET /locations/{id}/hotspots/
    resp_hotspots = client.get(f'/api/v1/locations/{loc1.id}/hotspots/')
    assert resp_hotspots.status_code == 200
    assert len(resp_hotspots.data) == 1
    assert resp_hotspots.data[0]['slug'] == 'kariakoo-wifi'

    # 3. GET /locations/{id}/sessions/
    resp_sessions = client.get(f'/api/v1/locations/{loc1.id}/sessions/')
    assert resp_sessions.status_code == 200
    assert len(resp_sessions.data) == 1
    assert resp_sessions.data[0]['username'] == '0712345678'

    # 4. POST /locations/{id}/move-router/ -> Move router1 from loc1 to loc2
    resp_move = client.post(f'/api/v1/locations/{loc2.id}/move-router/', {
        'router_id': str(router1.id)
    }, format='json')
    assert resp_move.status_code == 200
    assert resp_move.data['action'] == 'moved'

    router1.refresh_from_db()
    assert router1.location == loc2


@pytest.mark.django_db
def test_location_tenant_isolation(location_api_setup):
    client = APIClient()
    user_b = location_api_setup['user_b']
    loc1 = location_api_setup['loc1']
    router1 = location_api_setup['router1']
    loc_b = location_api_setup['loc_b']

    client.force_authenticate(user=user_b)

    # User B cannot view Tenant A's location
    resp_get = client.get(f'/api/v1/locations/{loc1.id}/')
    assert resp_get.status_code == 404

    # User B cannot edit Tenant A's location
    resp_patch = client.patch(f'/api/v1/locations/{loc1.id}/', {'name': 'Hacked'})
    assert resp_patch.status_code == 404

    # User B cannot delete Tenant A's location
    resp_del = client.delete(f'/api/v1/locations/{loc1.id}/')
    assert resp_del.status_code == 404

    # User B cannot move Tenant A's router into Tenant B's location
    resp_move = client.post(f'/api/v1/locations/{loc_b.id}/move-router/', {
        'router_id': str(router1.id)
    }, format='json')
    assert resp_move.status_code == 404
