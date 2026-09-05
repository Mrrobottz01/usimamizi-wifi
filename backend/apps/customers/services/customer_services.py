import logging
import re
from typing import Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.companies.models import Company
from apps.radius.services.radius_services import normalize_mac_address
from ..models import (
    Customer,
    CustomerDevice,
    CustomerStatus,
    DeviceType,
    Subscription,
    SubscriptionStatus,
)

logger = logging.getLogger(__name__)


def normalize_customer_phone(phone: str) -> str:
    """
    Normalize Tanzanian phone number to standard canonical E.164 (+2557XXXXXXXX or +2556XXXXXXXX).
    Accepts formats like:
      - 0712345678
      - 712345678
      - 255712345678
      - +255712345678
      - +255 712-345 678
    """
    if not phone:
        return ''
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone.strip())
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]

    # Strip leading zero if present
    if cleaned.startswith('0'):
        cleaned = cleaned[1:]

    # Prepend 255 if starts with 7 or 6
    if cleaned.startswith(('6', '7')) and len(cleaned) == 9:
        cleaned = '255' + cleaned

    if not cleaned.startswith('255'):
        # Fallback if international
        return f"+{cleaned}"

    return f"+{cleaned}"


@transaction.atomic
def get_or_create_customer(
    company: Company,
    phone: str,
    first_name: str = '',
    last_name: str = '',
    email: str = '',
    language: str = 'EN'
) -> Tuple[Customer, bool]:
    """
    Resolve or create persistent customer identity by canonical normalized phone.
    Guarantees strict tenant isolation and idempotent lookup.
    """
    normalized = normalize_customer_phone(phone)
    if not normalized:
        raise ValueError("Valid customer phone number is required.")

    customer = Customer.objects.select_for_update().filter(
        company=company,
        normalized_phone=normalized
    ).first()

    created = False
    if not customer:
        customer = Customer.objects.create(
            company=company,
            phone=phone.strip(),
            normalized_phone=normalized,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email.strip().lower(),
            language=language,
            last_seen_at=timezone.now(),
        )
        created = True
    else:
        # Update last seen and any missing fields
        updated_fields = ['last_seen_at']
        customer.last_seen_at = timezone.now()
        if first_name and not customer.first_name:
            customer.first_name = first_name.strip()
            updated_fields.append('first_name')
        if last_name and not customer.last_name:
            customer.last_name = last_name.strip()
            updated_fields.append('last_name')
        if email and not customer.email:
            customer.email = email.strip().lower()
            updated_fields.append('email')
        customer.save(update_fields=updated_fields)

    return customer, created


@transaction.atomic
def register_or_update_device(
    customer: Customer,
    mac_address: str,
    device_name: str = '',
    device_type: str = DeviceType.MOBILE,
    metadata: Optional[dict] = None
) -> Tuple[CustomerDevice, bool]:
    """
    Register or touch a physical device MAC address belonging to a customer.
    """
    norm_mac = normalize_mac_address(mac_address)
    if not norm_mac or norm_mac == '00:00:00:00:00:00':
        return None, False

    device = CustomerDevice.objects.select_for_update().filter(
        customer=customer,
        mac_address=norm_mac
    ).first()

    created = False
    now = timezone.now()
    if not device:
        device = CustomerDevice.objects.create(
            company=customer.company,
            customer=customer,
            mac_address=norm_mac,
            device_name=device_name.strip() or f"Device ({norm_mac[-5:]})",
            device_type=device_type,
            metadata=metadata or {},
        )
        created = True
    else:
        device.last_seen_at = now
        if device_name and not device.device_name:
            device.device_name = device_name.strip()
        if metadata:
            device.metadata = {**device.metadata, **metadata}
        device.save(update_fields=['last_seen_at', 'device_name', 'metadata'])

    return device, created


@transaction.atomic
def block_customer(customer: Customer, reason: str = '', user=None) -> Customer:
    """
    Block customer from network. Revokes active subscriptions and disconnects live sessions.
    """
    from .subscription_services import suspend_subscription

    old_status = customer.status
    customer.status = CustomerStatus.BLOCKED
    if reason:
        customer.notes = f"{customer.notes}\n[BLOCKED at {timezone.now().isoformat()}]: {reason}".strip()
    customer.save(update_fields=['status', 'notes', 'updated_at'])

    # Suspend all active subscriptions
    active_subs = customer.subscriptions.filter(status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE])
    for sub in active_subs:
        suspend_subscription(sub, reason=f"Customer blocked: {reason}", user=user)

    AuditLog.objects.create(
        company=customer.company,
        user=user,
        action='CUSTOMER_BLOCKED',
        resource_type='Customer',
        resource_id=str(customer.id),
        changes={'old_status': old_status, 'new_status': CustomerStatus.BLOCKED, 'reason': reason}
    )

    return customer


@transaction.atomic
def suspend_customer(customer: Customer, reason: str = '', user=None) -> Customer:
    """
    Suspend customer. Suspends all active subscriptions.
    """
    from .subscription_services import suspend_subscription

    old_status = customer.status
    customer.status = CustomerStatus.SUSPENDED
    if reason:
        customer.notes = f"{customer.notes}\n[SUSPENDED at {timezone.now().isoformat()}]: {reason}".strip()
    customer.save(update_fields=['status', 'notes', 'updated_at'])

    active_subs = customer.subscriptions.filter(status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE])
    for sub in active_subs:
        suspend_subscription(sub, reason=f"Customer suspended: {reason}", user=user)

    AuditLog.objects.create(
        company=customer.company,
        user=user,
        action='CUSTOMER_SUSPENDED',
        resource_type='Customer',
        resource_id=str(customer.id),
        changes={'old_status': old_status, 'new_status': CustomerStatus.SUSPENDED, 'reason': reason}
    )

    return customer


@transaction.atomic
def reactivate_customer(customer: Customer, user=None) -> Customer:
    """
    Reactivate suspended or blocked customer back to ACTIVE.
    """
    old_status = customer.status
    customer.status = CustomerStatus.ACTIVE
    customer.save(update_fields=['status', 'updated_at'])

    AuditLog.objects.create(
        company=customer.company,
        user=user,
        action='CUSTOMER_REACTIVATED',
        resource_type='Customer',
        resource_id=str(customer.id),
        changes={'old_status': old_status, 'new_status': CustomerStatus.ACTIVE}
    )

    return customer
