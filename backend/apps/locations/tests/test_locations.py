from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.companies.models import Company
from apps.locations.models import Location, LocationStatus, generate_location_code


@pytest.fixture
def companies(db):
    c1 = Company.objects.create(name="Arusha Hotspot Ltd", slug="arusha-wifi")
    c2 = Company.objects.create(name="Dar Hotspot Ltd", slug="dar-wifi")
    return c1, c2


@pytest.mark.django_db
def test_create_location_with_code_generation(companies):
    comp1, _ = companies
    loc = Location.objects.create(
        company=comp1,
        name="Clocktower Branch",
        region="Arusha",
        district="Arusha Urban",
        status=LocationStatus.ACTIVE,
    )
    assert loc.id is not None
    assert loc.code.startswith("LOC-CLO-")
    assert loc.is_active is True
    assert loc.status == LocationStatus.ACTIVE


@pytest.mark.django_db
def test_location_company_isolation(companies):
    comp1, comp2 = companies
    loc1 = Location.objects.create(company=comp1, name="Branch 1", code="LOC-001")
    loc2 = Location.objects.create(company=comp2, name="Branch 1", code="LOC-001")

    assert loc1.code == loc2.code
    assert loc1.company != loc2.company
    assert Location.objects.filter(company=comp1).count() == 1
    assert Location.objects.filter(company=comp2).count() == 1


@pytest.mark.django_db
def test_location_code_uniqueness_within_company(companies):
    comp1, _ = companies
    Location.objects.create(company=comp1, name="Branch A", code="LOC-DUP-001")
    with pytest.raises(IntegrityError):
        Location.objects.create(company=comp1, name="Branch B", code="LOC-DUP-001")


@pytest.mark.django_db
def test_location_coordinate_validation(companies):
    comp1, _ = companies
    loc_invalid_lat = Location(
        company=comp1,
        name="Invalid Lat",
        code="LOC-INV-001",
        latitude=Decimal("95.123456"),
        longitude=Decimal("39.123456"),
    )
    with pytest.raises(ValidationError) as exc:
        loc_invalid_lat.full_clean()
    assert "latitude" in exc.value.message_dict

    loc_invalid_lng = Location(
        company=comp1,
        name="Invalid Lng",
        code="LOC-INV-002",
        latitude=Decimal("-6.123456"),
        longitude=Decimal("195.123456"),
    )
    with pytest.raises(ValidationError) as exc:
        loc_invalid_lng.full_clean()
    assert "longitude" in exc.value.message_dict


@pytest.mark.django_db
def test_generate_location_code_increment(companies):
    comp1, _ = companies
    code1 = generate_location_code(comp1, "Main")
    assert code1 == "LOC-MAI-001"
    Location.objects.create(company=comp1, name="Main", code=code1)

    code2 = generate_location_code(comp1, "Main")
    assert code2 == "LOC-MAI-002"
