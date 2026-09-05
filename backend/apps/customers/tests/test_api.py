from decimal import Decimal
from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.companies.models import Company, CompanyMembership, HotspotConfiguration
from apps.customers.models import Customer, CustomerOTP, CustomerSubscriptionSettings
from apps.customers.services.customer_services import get_or_create_customer
from apps.customers.services.otp_services import _hash_otp, generate_customer_token
from apps.plans.models import DurationUnit, Plan, ValidityMode

User = get_user_model()


@pytest.fixture
def api_setup(db):
    user = User.objects.create_user(email="admin@hotspot.tz", password="password123")
    company = Company.objects.create(name="Hotspot Hub Arusha", slug="arusha")
    CompanyMembership.objects.create(user=user, company=company, is_active=True)
    hotspot = HotspotConfiguration.objects.create(
        company=company,
        slug="hub-lobby",
        ssid="Usimamizi-WiFi-Lab",
        is_active=True,
    )
    plan = Plan.objects.create(
        company=company,
        name="Daily Pass",
        code="DAILY-5M",
        price=Decimal("2000.00"),
        currency="TZS",
        duration_value=1,
        duration_unit=DurationUnit.DAYS,
        validity_mode=ValidityMode.CALENDAR,
        download_speed_kbps=5120,
        upload_speed_kbps=2048,
        is_active=True,
    )
    client = APIClient()
    return client, user, company, hotspot, plan


@pytest.mark.django_db
def test_admin_customers_list_and_metrics(api_setup):
    client, user, company, hotspot, plan = api_setup
    client.force_authenticate(user=user)

    c1, _ = get_or_create_customer(company=company, phone="0712345678", first_name="Amina")
    c2, _ = get_or_create_customer(company=company, phone="0784112233", first_name="Bakari")

    res = client.get(f"/api/v1/customers/?company_id={company.id}")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert data["metrics"]["total_customers"] == 2
    assert len(data["results"]) == 2


@pytest.mark.django_db
@patch('apps.customers.services.otp_services.route_and_send_sms')
def test_public_customer_portal_otp_and_me_flow(mock_send_sms, api_setup):
    client, _, company, hotspot, plan = api_setup

    # 1. Request OTP
    req_res = client.post("/api/v1/public/customer/request-otp/", {
        "phone": "0712345678",
        "slug": hotspot.slug,
    })
    assert req_res.status_code == 200
    assert req_res.json()["code"] == "otp_sent"

    # Fetch OTP record
    otp_record = CustomerOTP.objects.filter(company=company, phone="+255712345678").first()
    assert otp_record is not None

    # Inject known code for test
    known_code = "998877"
    otp_record.otp_hash = _hash_otp(known_code)
    otp_record.save(update_fields=['otp_hash'])

    # 2. Verify OTP
    verify_res = client.post("/api/v1/public/customer/verify-otp/", {
        "phone": "0712345678",
        "code": known_code,
        "slug": hotspot.slug,
    })
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["code"] == "verified"
    token = verify_data["token"]
    assert token is not None

    # 3. Access /me with token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    me_res = client.get("/api/v1/public/customer/me/")
    assert me_res.status_code == 200
    assert me_res.json()["normalized_phone"] == "+255712345678"

    # 4. Access /subscription
    sub_res = client.get("/api/v1/public/customer/subscription/")
    assert sub_res.status_code == 200
