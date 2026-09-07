import pytest
from django.core.exceptions import ValidationError
from apps.companies.models import Company
from apps.locations.models import Location
from apps.radius.models import RadiusClient
from apps.routers.models import Router, RouterHealthStatus


@pytest.fixture
def topology(db):
    comp1 = Company.objects.create(name="Company Arusha", slug="arusha")
    comp2 = Company.objects.create(name="Company Dar", slug="dar")
    loc1 = Location.objects.create(company=comp1, name="Arusha Central", code="LOC-ARU-01")
    loc2 = Location.objects.create(company=comp2, name="Dar Central", code="LOC-DAR-01")
    return comp1, comp2, loc1, loc2


@pytest.mark.django_db
def test_create_router_and_credential_encryption(topology):
    comp1, _, loc1, _ = topology
    router = Router.objects.create(
        company=comp1,
        location=loc1,
        name="MikroTik-Arusha-01",
        identity="mikrotik-core",
        vendor="MikroTik",
        model="RB4011iGS+",
        serial_number="HE401199AA",
        management_ip="192.168.10.1",
        api_port=8728,
        api_username="admin",
        health_status=RouterHealthStatus.ONLINE,
    )
    router.api_password = "super-secret-router-password"
    router.save()

    # Verify at-rest encryption
    router.refresh_from_db()
    assert router.api_password_encrypted != "super-secret-router-password"
    assert router.api_password == "super-secret-router-password"
    assert router.health_status == RouterHealthStatus.ONLINE


@pytest.mark.django_db
def test_router_location_company_consistency(topology):
    comp1, comp2, loc1, loc2 = topology

    # Attempt to assign Location from comp2 to Router of comp1
    cross_router = Router(
        company=comp1,
        location=loc2,  # Belongs to comp2!
        name="Mismatched Router",
        management_ip="10.0.0.1",
    )
    with pytest.raises(ValidationError) as exc:
        cross_router.full_clean()
    assert "location" in exc.value.message_dict


@pytest.mark.django_db
def test_router_radius_client_relationship(topology):
    comp1, _, loc1, _ = topology
    router = Router.objects.create(
        company=comp1,
        location=loc1,
        name="Hotspot Gateway",
        management_ip="10.5.50.1",
    )
    nas = RadiusClient.objects.create(
        company=comp1,
        router=router,
        name="FreeRADIUS NAS",
        nas_ip="10.5.50.1",
        nas_identifier="lab_hap_ac_lite",
    )

    assert nas.router == router
    assert router.radius_client == nas


@pytest.mark.django_db
def test_multiple_routers_at_single_location(topology):
    comp1, _, loc1, _ = topology
    r1 = Router.objects.create(company=comp1, location=loc1, name="Floor 1 AP", management_ip="10.5.50.1")
    r2 = Router.objects.create(company=comp1, location=loc1, name="Floor 2 AP", management_ip="10.5.50.2")
    r3 = Router.objects.create(company=comp1, location=loc1, name="Outdoor AP", management_ip="10.5.50.3")

    assert loc1.routers.count() == 3
    assert set(loc1.routers.values_list('name', flat=True)) == {"Floor 1 AP", "Floor 2 AP", "Outdoor AP"}


@pytest.mark.django_db
def test_router_api_port_validation(topology):
    comp1, _, loc1, _ = topology
    r = Router(
        company=comp1,
        location=loc1,
        name="Bad Port Router",
        management_ip="10.5.50.1",
        api_port=70000,
    )
    with pytest.raises(ValidationError) as exc:
        r.full_clean()
    assert "api_port" in exc.value.message_dict
