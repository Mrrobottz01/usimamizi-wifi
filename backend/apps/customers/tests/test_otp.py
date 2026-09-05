from datetime import timedelta
from unittest.mock import patch
import pytest
from django.utils import timezone

from apps.companies.models import Company
from apps.customers.models import Customer, CustomerOTP, CustomerStatus
from apps.customers.services.otp_services import (
    _hash_otp,
    authenticate_customer_token,
    generate_and_send_customer_otp,
    generate_customer_token,
    verify_customer_otp,
)


@pytest.fixture
def company(db):
    return Company.objects.create(name="Hotspot Hub Arusha", slug="arusha")


@pytest.mark.django_db
@patch('apps.customers.services.otp_services.route_and_send_sms')
def test_generate_and_send_otp(mock_send_sms, company):
    phone = "0712345678"
    success, msg, cooldown = generate_and_send_customer_otp(company=company, phone=phone)

    assert success is True
    assert cooldown is None
    mock_send_sms.assert_called_once()

    otp = CustomerOTP.objects.filter(company=company, phone="+255712345678").first()
    assert otp is not None
    assert otp.is_used is False
    assert len(otp.otp_hash) == 64  # SHA-256


@pytest.mark.django_db
@patch('apps.customers.services.otp_services.route_and_send_sms')
def test_otp_resend_cooldown(mock_send_sms, company):
    phone = "0712345678"
    generate_and_send_customer_otp(company=company, phone=phone)

    # Immediate second attempt
    success2, msg2, cooldown2 = generate_and_send_customer_otp(company=company, phone=phone)
    assert success2 is False
    assert cooldown2 is not None
    assert "Please wait" in msg2


@pytest.mark.django_db
def test_verify_otp_attempt_limits_and_success(company):
    phone = "0784112233"
    code = "584920"
    otp_hash = _hash_otp(code)

    CustomerOTP.objects.create(
        company=company,
        phone="+255784112233",
        otp_hash=otp_hash,
        expires_at=timezone.now() + timedelta(minutes=5),
        attempts=0,
    )

    # Attempt 1: wrong code
    ok, msg, cust, token = verify_customer_otp(company=company, phone=phone, code="000000")
    assert ok is False
    assert "Incorrect code" in msg
    assert token is None

    # Attempt 2: correct code
    ok2, msg2, cust2, token2 = verify_customer_otp(company=company, phone=phone, code=code)
    assert ok2 is True
    assert cust2 is not None
    assert cust2.normalized_phone == "+255784112233"
    assert token2 is not None

    # Authenticate token
    authenticated_cust = authenticate_customer_token(token2)
    assert authenticated_cust is not None
    assert authenticated_cust.id == cust2.id


@pytest.mark.django_db
def test_tampered_or_expired_token(company):
    from apps.customers.services.customer_services import get_or_create_customer
    customer, _ = get_or_create_customer(company=company, phone="0712345678")

    token = generate_customer_token(customer)
    tampered_token = token + "bad"

    assert authenticate_customer_token(tampered_token) is None
    # Expired token test (max_age=-1)
    assert authenticate_customer_token(token, max_age=-1) is None
