import pytest
from django.utils import timezone

from apps.companies.models import Company
from apps.customers.models import Customer, CustomerDevice, CustomerStatus, DeviceType
from apps.customers.services.customer_services import (
    block_customer,
    get_or_create_customer,
    normalize_customer_phone,
    reactivate_customer,
    register_or_update_device,
    suspend_customer,
)


@pytest.fixture
def test_companies(db):
    comp1 = Company.objects.create(name="Hotspot Hub Arusha", slug="arusha")
    comp2 = Company.objects.create(name="Hotspot Hub Dar", slug="dar")
    return comp1, comp2


@pytest.mark.django_db
def test_phone_normalization():
    assert normalize_customer_phone("0712345678") == "+255712345678"
    assert normalize_customer_phone("255712345678") == "+255712345678"
    assert normalize_customer_phone("+255712345678") == "+255712345678"
    assert normalize_customer_phone("+255 712-345 678") == "+255712345678"
    assert normalize_customer_phone("0655123456") == "+255655123456"
    assert normalize_customer_phone("+255 655 123 456") == "+255655123456"


@pytest.mark.django_db
def test_get_or_create_customer_canonicalization(test_companies):
    comp1, _ = test_companies

    c1, created1 = get_or_create_customer(company=comp1, phone="0784112233", first_name="Juma")
    assert created1 is True
    assert c1.normalized_phone == "+255784112233"
    assert c1.first_name == "Juma"

    # Secondary lookup with different formatting returns identical record
    c2, created2 = get_or_create_customer(company=comp1, phone="+255 784-112 233")
    assert created2 is False
    assert c1.id == c2.id
    assert c2.first_name == "Juma"


@pytest.mark.django_db
def test_tenant_isolation(test_companies):
    comp1, comp2 = test_companies
    phone = "0712345678"

    c1, _ = get_or_create_customer(company=comp1, phone=phone)
    c2, _ = get_or_create_customer(company=comp2, phone=phone)

    assert c1.company_id == comp1.id
    assert c2.company_id == comp2.id
    assert c1.id != c2.id


@pytest.mark.django_db
def test_device_registration(test_companies):
    comp, _ = test_companies
    cust, _ = get_or_create_customer(company=comp, phone="0712345678")

    # Register MAC with colons / lowercase
    dev, created = register_or_update_device(
        customer=cust,
        mac_address="aa-bb-cc-dd-ee-ff",
        device_name="Samsung A52",
        device_type=DeviceType.MOBILE,
    )
    assert created is True
    assert dev.mac_address == "AA:BB:CC:DD:EE:FF"
    assert dev.customer == cust
    assert dev.is_trusted is True
    assert dev.is_blocked is False

    # Second call updates last seen
    dev2, created2 = register_or_update_device(customer=cust, mac_address="AA:BB:CC:DD:EE:FF")
    assert created2 is False
    assert dev.id == dev2.id
    assert cust.devices.count() == 1


@pytest.mark.django_db
def test_customer_lifecycle_actions(test_companies):
    comp, _ = test_companies
    cust, _ = get_or_create_customer(company=comp, phone="0712345678")
    assert cust.status == CustomerStatus.ACTIVE

    # Suspend
    suspended = suspend_customer(cust, reason="Terms violation")
    assert suspended.status == CustomerStatus.SUSPENDED

    # Reactivate
    reactivated = reactivate_customer(suspended)
    assert reactivated.status == CustomerStatus.ACTIVE

    # Block
    blocked = block_customer(reactivated, reason="Payment fraud")
    assert blocked.status == CustomerStatus.BLOCKED
