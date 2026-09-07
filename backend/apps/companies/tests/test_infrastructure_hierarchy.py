import pytest
from django.core.exceptions import ValidationError
from apps.companies.models import Company, HotspotConfiguration, RouterUplinkProfile
from apps.locations.models import Location
from apps.routers.models import Router


@pytest.fixture
def hierarchy_setup(db):
    comp = Company.objects.create(name="Serengeti Safari WiFi", slug="serengeti")
    loc = Location.objects.create(company=comp, name="Serengeti Main Lodge", code="LOC-SRG-001")
    router = Router.objects.create(
        company=comp,
        location=loc,
        name="Lodge-Core-Router",
        management_ip="10.10.0.1"
    )
    return comp, loc, router


@pytest.mark.django_db
def test_hotspot_linked_to_router_and_location(hierarchy_setup):
    comp, loc, router = hierarchy_setup
    hs = HotspotConfiguration.objects.create(
        company=comp,
        location=loc,
        router=router,
        name="Lodge Guest HotSpot",
        slug="serengeti-guest",
        ssid="Serengeti-Lodge-WiFi",
        gateway_ip="10.10.0.1",
        interface_name="bridgeLocal",
        server_name="hotspot-guest",
    )

    assert hs.location == loc
    assert hs.router == router
    assert hs.gateway_ip == "10.10.0.1"
    assert hs.interface_name == "bridgeLocal"
    assert hs.server_name == "hotspot-guest"
    assert loc.hotspots.count() == 1
    assert router.hotspots.count() == 1


@pytest.mark.django_db
def test_one_router_hosts_multiple_hotspots(hierarchy_setup):
    comp, loc, router = hierarchy_setup
    hs_guest = HotspotConfiguration.objects.create(
        company=comp,
        location=loc,
        router=router,
        name="Guest Wi-Fi",
        slug="lodge-guest",
        ssid="Lodge-Guest",
        interface_name="vlan10-guest",
        server_name="hotspot-guest",
    )
    hs_vip = HotspotConfiguration.objects.create(
        company=comp,
        location=loc,
        router=router,
        name="VIP Lounge Wi-Fi",
        slug="lodge-vip",
        ssid="Lodge-VIP",
        interface_name="vlan20-vip",
        server_name="hotspot-vip",
    )
    hs_staff = HotspotConfiguration.objects.create(
        company=comp,
        location=loc,
        router=router,
        name="Staff Wi-Fi",
        slug="lodge-staff",
        ssid="Lodge-Staff",
        interface_name="vlan30-staff",
        server_name="hotspot-staff",
    )

    assert router.hotspots.count() == 3
    assert set(router.hotspots.values_list('slug', flat=True)) == {
        "lodge-guest", "lodge-vip", "lodge-staff"
    }


@pytest.mark.django_db
def test_hotspot_location_router_company_consistency(hierarchy_setup):
    comp, loc, router = hierarchy_setup
    other_comp = Company.objects.create(name="Other Resort", slug="other-resort")
    other_loc = Location.objects.create(company=other_comp, name="Other Branch", code="LOC-OTH-001")

    # Mismatched location company
    bad_hs = HotspotConfiguration(
        company=comp,
        location=other_loc,
        router=router,
        name="Cross Company HotSpot",
        slug="cross-comp",
    )
    with pytest.raises(ValidationError) as exc:
        bad_hs.full_clean()
    assert "location" in exc.value.message_dict


@pytest.mark.django_db
def test_existing_hotspot_singleton_query_compatibility(hierarchy_setup):
    comp, loc, router = hierarchy_setup
    hs = HotspotConfiguration.objects.create(
        company=comp,
        location=loc,
        router=router,
        name="Primary HotSpot",
        slug="primary-hs",
        ssid="Primary-WiFi",
    )

    # Legacy services rely on: HotspotConfiguration.objects.filter(company=company).first()
    first_hs = HotspotConfiguration.objects.filter(company=comp).first()
    assert first_hs is not None
    assert first_hs.id == hs.id
    assert first_hs.slug == "primary-hs"


@pytest.mark.django_db
def test_router_uplink_profile_linked_to_router(hierarchy_setup):
    comp, _, router = hierarchy_setup
    profile = RouterUplinkProfile.objects.create(
        company=comp,
        router=router,
        name="Airtel Backup 5G",
        ssid="Airtel_5G_Lodge",
        password="secretpassword",
        is_active=True,
    )

    assert profile.router == router
    assert router.uplink_profiles.count() == 1
    # Backward compatibility: company-scoped queries still work
    assert comp.uplink_profiles.filter(is_active=True).count() == 1
