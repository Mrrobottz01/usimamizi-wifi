import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.companies.models import Company, CompanyMembership, HotspotConfiguration
from apps.locations.models import Location, LocationStatus, SiteType
from apps.locations.services.location_services import (
    calculate_location_network_health,
    deactivate_location,
    move_router_to_location,
    reactivate_location,
    safe_delete_location,
)
from apps.routers.models import Router, RouterHealthStatus


@pytest.fixture
def location_setup(db):
    user_a = User.objects.create_user(email='admin@site-a.com', password='Password123!')
    company_a = Company.objects.create(name='Tenant A', slug='tenant-a')
    CompanyMembership.objects.create(company=company_a, user=user_a, is_active=True)

    loc1 = Location.objects.create(
        company=company_a,
        name='Kariakoo Branch',
        code='LOC-KAR-001',
        region='Dar es Salaam',
        district='Ilala',
        site_type=SiteType.BRANCH,
        status=LocationStatus.ACTIVE,
    )
    loc2 = Location.objects.create(
        company=company_a,
        name='Mbezi Beach Resort',
        code='LOC-MBE-001',
        region='Dar es Salaam',
        district='Kinondoni',
        site_type=SiteType.HOTEL,
        status=LocationStatus.ACTIVE,
    )

    # User & Company B (Tenant isolation)
    user_b = User.objects.create_user(email='admin@site-b.com', password='Password123!')
    company_b = Company.objects.create(name='Tenant B', slug='tenant-b')
    CompanyMembership.objects.create(company=company_b, user=user_b, is_active=True)
    loc_b = Location.objects.create(
        company=company_b,
        name='Arusha Hotel',
        code='LOC-ARU-001',
        site_type=SiteType.HOTEL,
    )

    return {
        'user_a': user_a,
        'company_a': company_a,
        'loc1': loc1,
        'loc2': loc2,
        'user_b': user_b,
        'company_b': company_b,
        'loc_b': loc_b,
    }


@pytest.mark.django_db
def test_calculate_network_health_states(location_setup):
    loc = location_setup['loc1']
    company = location_setup['company_a']

    # 1. No routers -> UNKNOWN
    health, summary = calculate_location_network_health(loc)
    assert health == 'UNKNOWN'
    assert summary['router_count'] == 0

    # 2. Add router 1 ONLINE -> HEALTHY
    now = timezone.now()
    r1 = Router.objects.create(
        company=company,
        location=loc,
        name='Router 1',
        management_ip='10.0.0.1',
        health_status=RouterHealthStatus.ONLINE,
        last_health_check_at=now,
    )
    health, summary = calculate_location_network_health(loc)
    assert health == 'HEALTHY'
    assert summary['router_count'] == 1
    assert summary['online_router_count'] == 1
    assert summary['last_network_update_at'] == now.isoformat()

    # 3. Add router 2 UNREACHABLE -> DEGRADED (some online, some unreachable)
    r2 = Router.objects.create(
        company=company,
        location=loc,
        name='Router 2',
        management_ip='10.0.0.2',
        health_status=RouterHealthStatus.UNREACHABLE,
    )
    health, summary = calculate_location_network_health(loc)
    assert health == 'DEGRADED'
    assert summary['router_count'] == 2
    assert summary['online_router_count'] == 1
    assert summary['unreachable_router_count'] == 1

    # 4. Router 1 becomes OFFLINE -> OFFLINE (active routers exist, none online)
    r1.health_status = RouterHealthStatus.OFFLINE
    r1.save()
    health, summary = calculate_location_network_health(loc)
    assert health == 'OFFLINE'
    assert summary['online_router_count'] == 0

    # 5. Inactive router excluded from active calculation
    r1.is_active = False
    r1.save()
    health, summary = calculate_location_network_health(loc)
    assert summary['router_count'] == 1  # only r2 is active


@pytest.mark.django_db
def test_move_router_to_location_service(location_setup):
    loc1 = location_setup['loc1']
    loc2 = location_setup['loc2']
    company = location_setup['company_a']
    user = location_setup['user_a']

    router = Router.objects.create(
        company=company,
        location=loc1,
        name='Main-GW',
        management_ip='10.0.0.1'
    )
    hs1 = HotspotConfiguration.objects.create(
        company=company,
        location=loc1,
        router=router,
        name='Guest HotSpot',
        slug='guest-hs'
    )

    # 1. Relocate router to loc2
    updated = move_router_to_location(router=router, new_location=loc2, user=user)
    assert updated.location == loc2

    # Verify hosted hotspot location was automatically updated to match hosting router
    hs1.refresh_from_db()
    assert hs1.location == loc2

    # Verify audit trail
    log = AuditLog.objects.filter(action='ROUTER_MOVED_LOCATION', resource_id=str(router.id)).first()
    assert log is not None
    assert log.changes['to_location_id'] == str(loc2.id)

    # 2. Cross-company relocation rejected
    loc_b = location_setup['loc_b']
    with pytest.raises(ValidationError):
        move_router_to_location(router=router, new_location=loc_b, user=user)


@pytest.mark.django_db
def test_deactivate_and_reactivate_location(location_setup):
    loc = location_setup['loc1']
    user = location_setup['user_a']

    deactivate_location(location=loc, user=user)
    loc.refresh_from_db()
    assert loc.is_active is False
    assert loc.status == LocationStatus.INACTIVE
    assert AuditLog.objects.filter(action='LOCATION_DEACTIVATED', resource_id=str(loc.id)).exists()

    reactivate_location(location=loc, user=user)
    loc.refresh_from_db()
    assert loc.is_active is True
    assert loc.status == LocationStatus.ACTIVE
    assert AuditLog.objects.filter(action='LOCATION_REACTIVATED', resource_id=str(loc.id)).exists()


@pytest.mark.django_db
def test_safe_delete_location(location_setup):
    loc = location_setup['loc1']
    company = location_setup['company_a']
    user = location_setup['user_a']

    # Case A: Location has a router -> Safe deactivation instead of hard delete
    r = Router.objects.create(company=company, location=loc, name='GW', management_ip='10.0.0.1')
    action, msg = safe_delete_location(location=loc, user=user)
    assert action == 'deactivated'
    assert 'was deactivated rather than deleted' in msg

    loc.refresh_from_db()
    assert loc.is_active is False
    assert Location.objects.filter(id=loc.id).exists()

    # Case B: Completely unreferenced location -> permanent deletion
    loc_empty = location_setup['loc2']
    loc_id = loc_empty.id
    action_del, msg_del = safe_delete_location(location=loc_empty, user=user)
    assert action_del == 'deleted'
    assert not Location.objects.filter(id=loc_id).exists()
    assert AuditLog.objects.filter(action='LOCATION_DELETED', resource_id=str(loc_id)).exists()
