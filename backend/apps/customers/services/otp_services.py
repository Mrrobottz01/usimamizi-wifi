import hashlib
import logging
import secrets
from datetime import timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.companies.models import Company
from apps.notifications.models import NotificationMessage, NotificationStatus
from apps.notifications.services.sms_services import route_and_send_sms
from .customer_services import get_or_create_customer, normalize_customer_phone
from ..models import (
    Customer,
    CustomerOTP,
    CustomerStatus,
    CustomerSubscriptionSettings,
)

logger = logging.getLogger(__name__)

CUSTOMER_TOKEN_SALT = 'customer-portal-session-auth'
DEFAULT_TOKEN_MAX_AGE = 86400 * 7  # 7 days


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.strip().encode('utf-8')).hexdigest()


def generate_and_send_customer_otp(
    company: Company,
    phone: str,
    hotspot=None,
) -> Tuple[bool, str, Optional[int]]:
    """
    Generates a secure 6-digit one-time passcode, hashes it, stores it in CustomerOTP,
    and dispatches an SMS to the customer via RafikiSMS.

    Returns:
        (success: bool, message: str, cooldown_remaining: Optional[int])
    """
    normalized_phone = normalize_customer_phone(phone)
    if not normalized_phone:
        return False, "Invalid phone number provided.", None

    # Check if customer exists and is blocked
    existing_customer = Customer.objects.filter(
        company=company,
        normalized_phone=normalized_phone,
    ).first()
    if existing_customer and existing_customer.status == CustomerStatus.BLOCKED:
        return False, "This account has been blocked. Please contact support.", None

    # Load or initialize tenant subscription settings
    sub_settings, _ = CustomerSubscriptionSettings.objects.get_or_create(company=company)

    # Check cooldown against recent OTPs
    cooldown_seconds = sub_settings.otp_resend_cooldown_seconds
    recent_otp = CustomerOTP.objects.filter(
        company=company,
        phone=normalized_phone,
        created_at__gte=timezone.now() - timedelta(seconds=cooldown_seconds),
    ).order_by('-created_at').first()

    if recent_otp:
        elapsed = int((timezone.now() - recent_otp.created_at).total_seconds())
        remaining = max(1, cooldown_seconds - elapsed)
        return False, f"Please wait {remaining} seconds before requesting a new code.", remaining

    # Generate 6-digit code securely
    plain_code = f"{secrets.randbelow(1000000):06d}"
    otp_hash = _hash_otp(plain_code)
    expires_at = timezone.now() + timedelta(minutes=sub_settings.otp_expiry_minutes)

    # Invalidate previous unexpired OTPs for this phone
    CustomerOTP.objects.filter(
        company=company,
        phone=normalized_phone,
        is_used=False,
    ).update(is_used=True)

    # Create OTP record (plaintext code is NEVER saved)
    CustomerOTP.objects.create(
        company=company,
        customer=existing_customer,
        phone=normalized_phone,
        otp_hash=otp_hash,
        expires_at=expires_at,
    )

    # Send SMS notification
    hotspot_name = hotspot.ssid if hotspot and hotspot.ssid else "Usimamizi Wi-Fi"
    sms_text = (
        f"Your {hotspot_name} verification code is: {plain_code}. "
        f"Valid for {sub_settings.otp_expiry_minutes} minutes. Do not share this code."
    )

    try:
        sms_record = NotificationMessage.objects.create(
            company=company,
            channel='SMS',
            recipient=normalized_phone,
            phone_normalized=normalized_phone,
            rendered_content=sms_text,
            status=NotificationStatus.QUEUED,
        )
        route_and_send_sms(notification_message=sms_record)
        logger.info(
            "Customer OTP dispatched via SMS to %s for company %s",
            normalized_phone,
            company.id,
        )
    except Exception as sms_err:
        logger.error(
            "Failed to dispatch customer OTP SMS to %s: %s",
            normalized_phone,
            sms_err,
        )
        # Even if SMS provider errors, return friendly message
        return True, "Verification code generated. If not received shortly, please retry.", None

    return True, "Verification code sent to your phone via SMS.", None


def verify_customer_otp(
    company: Company,
    phone: str,
    code: str,
) -> Tuple[bool, str, Optional[Customer], Optional[str]]:
    """
    Verifies the given 6-digit OTP code against the hashed record.
    Returns:
        (success: bool, message: str, customer: Optional[Customer], token: Optional[str])
    """
    normalized_phone = normalize_customer_phone(phone)
    if not normalized_phone or not code:
        return False, "Phone number and verification code are required.", None, None

    now = timezone.now()
    otp_record = CustomerOTP.objects.filter(
        company=company,
        phone=normalized_phone,
        is_used=False,
        expires_at__gt=now,
    ).order_by('-created_at').first()

    if not otp_record:
        return False, "Invalid or expired verification code. Please request a new one.", None, None

    # Check attempt limit
    if otp_record.attempts >= 3:
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])
        return False, "Too many invalid attempts. Please request a new code.", None, None

    # Verify cryptographic hash
    if _hash_otp(code) != otp_record.otp_hash:
        otp_record.attempts += 1
        otp_record.save(update_fields=['attempts'])
        remaining_attempts = max(0, 3 - otp_record.attempts)
        return False, f"Incorrect code. {remaining_attempts} attempt(s) remaining.", None, None

    # Success: Mark OTP as used
    otp_record.is_used = True
    otp_record.save(update_fields=['is_used'])

    # Resolve or create Customer identity
    if otp_record.customer:
        customer = otp_record.customer
    else:
        customer, _ = get_or_create_customer(
            company=company,
            phone=normalized_phone,
        )
        otp_record.customer = customer
        otp_record.save(update_fields=['customer'])

    if customer.status == CustomerStatus.BLOCKED:
        return False, "This account is blocked.", None, None

    customer.last_seen_at = now
    customer.save(update_fields=['last_seen_at', 'updated_at'])

    # Issue signed session token
    token = generate_customer_token(customer)
    return True, "Verification successful.", customer, token


def generate_customer_token(customer: Customer) -> str:
    """
    Generates a cryptographically signed, tamper-proof session token
    for the customer self-service portal.
    """
    payload = {
        'customer_id': str(customer.id),
        'company_id': str(customer.company_id),
        'phone': customer.normalized_phone,
        'created_at': timezone.now().isoformat(),
    }
    return signing.dumps(payload, salt=CUSTOMER_TOKEN_SALT)


def authenticate_customer_token(token: str, max_age: int = DEFAULT_TOKEN_MAX_AGE) -> Optional[Customer]:
    """
    Validates a signed customer portal token and returns the corresponding Customer.
    Returns None if signature is invalid, expired, or customer is blocked.
    """
    if not token:
        return None

    try:
        payload = signing.loads(
            token,
            salt=CUSTOMER_TOKEN_SALT,
            max_age=max_age,
        )
        customer_id = payload.get('customer_id')
        company_id = payload.get('company_id')

        customer = Customer.objects.filter(
            id=customer_id,
            company_id=company_id,
        ).exclude(status=CustomerStatus.BLOCKED).first()

        return customer
    except (signing.BadSignature, signing.SignatureExpired, Exception) as exc:
        logger.debug("Failed customer token authentication: %s", exc)
        return None
