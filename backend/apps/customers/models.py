import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.companies.models import Company, HotspotConfiguration
from apps.plans.models import Plan


class CustomerStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    BLOCKED = 'BLOCKED', 'Blocked'
    ARCHIVED = 'ARCHIVED', 'Archived'


class Customer(models.Model):
    """
    Persistent identity for returning Wi-Fi consumers.
    Identified primarily by canonical normalized phone number (+255...).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customers')

    phone = models.CharField(max_length=32, help_text="Original raw phone entered by customer.")
    normalized_phone = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Canonical E.164 phone (+2557XXXXXXXX)."
    )

    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    email = models.EmailField(blank=True, default='')

    status = models.CharField(
        max_length=32,
        choices=CustomerStatus.choices,
        default=CustomerStatus.ACTIVE,
        db_index=True
    )
    language = models.CharField(max_length=8, default='EN', choices=[('EN', 'English'), ('SW', 'Kiswahili')])
    notes = models.TextField(blank=True, default='')

    last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-last_seen_at', '-created_at']
        unique_together = ('company', 'normalized_phone')

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return f"{name or self.normalized_phone} ({self.status})"

    @property
    def display_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.normalized_phone


class DeviceType(models.TextChoices):
    MOBILE = 'MOBILE', 'Mobile Phone'
    LAPTOP = 'LAPTOP', 'Laptop / PC'
    TABLET = 'TABLET', 'Tablet'
    OTHER = 'OTHER', 'Other Device'


class CustomerDevice(models.Model):
    """
    Known client physical device associated with a customer.
    Stores normalized MAC address (EUI-48 format).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customer_devices')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='devices')

    mac_address = models.CharField(max_length=32, db_index=True, help_text="Normalized MAC address AA:BB:CC:DD:EE:FF")
    device_name = models.CharField(max_length=128, blank=True, default='')
    device_type = models.CharField(max_length=32, choices=DeviceType.choices, default=DeviceType.MOBILE)

    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True, db_index=True)

    is_trusted = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'customer_devices'
        verbose_name = 'Customer Device'
        verbose_name_plural = 'Customer Devices'
        ordering = ['-last_seen_at']
        unique_together = ('customer', 'mac_address')

    def __str__(self):
        return f"{self.device_name or 'Device'} [{self.mac_address}] - {self.customer.display_name}"


class SubscriptionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Payment'
    ACTIVE = 'ACTIVE', 'Active'
    GRACE = 'GRACE', 'Grace Period'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'


class SubscriptionSource(models.TextChoices):
    SELF_SERVICE_PAYMENT = 'SELF_SERVICE_PAYMENT', 'Self-Service Mobile Money'
    ADMIN_CREATED = 'ADMIN_CREATED', 'Administrator Created'
    VOUCHER_UPGRADE = 'VOUCHER_UPGRADE', 'Voucher Upgrade'
    PROMOTIONAL = 'PROMOTIONAL', 'Promotional Grant'
    MANUAL = 'MANUAL', 'Manual Grant'


class SubscriptionRenewalMode(models.TextChoices):
    MANUAL = 'MANUAL', 'Manual Renewal'
    AUTO_RENEW_FUTURE = 'AUTO_RENEW_FUTURE', 'Auto-Renew (Future)'


class Subscription(models.Model):
    """
    Commercial recurring access lifecycle contract for a customer.
    Yields sequential AccessEntitlement instances for RADIUS enforcement.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='subscriptions')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    hotspot = models.ForeignKey(
        HotspotConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions'
    )

    status = models.CharField(
        max_length=32,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
        db_index=True
    )

    started_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True, db_index=True)
    grace_period_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    renewal_mode = models.CharField(
        max_length=32,
        choices=SubscriptionRenewalMode.choices,
        default=SubscriptionRenewalMode.MANUAL
    )
    source = models.CharField(
        max_length=32,
        choices=SubscriptionSource.choices,
        default=SubscriptionSource.SELF_SERVICE_PAYMENT
    )

    plan_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Frozen snapshot of Plan commercial terms at activation/renewal."
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions'
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-current_period_end', '-created_at']

    def __str__(self):
        return f"{self.customer.display_name} — {self.plan.name} [{self.status}]"

    @property
    def is_valid_for_access(self) -> bool:
        now = timezone.now()
        if self.status == SubscriptionStatus.ACTIVE and self.current_period_end and self.current_period_end > now:
            return True
        return False

    @property
    def is_valid_now(self) -> bool:
        return self.is_valid_for_access

    @property
    def remaining_seconds(self) -> int:
        if not self.current_period_end:
            return 0
        now = timezone.now()
        return max(0, int((self.current_period_end - now).total_seconds()))


class SubscriptionEventType(models.TextChoices):
    CREATED = 'CREATED', 'Created'
    ACTIVATED = 'ACTIVATED', 'Activated'
    RENEWED = 'RENEWED', 'Renewed'
    GRACE_ENTERED = 'GRACE_ENTERED', 'Grace Period Entered'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    REACTIVATED = 'REACTIVATED', 'Reactivated'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'


class SubscriptionEvent(models.Model):
    """
    Immutable audit record tracking every lifecycle state transition of a subscription.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=32, choices=SubscriptionEventType.choices, db_index=True)

    old_status = models.CharField(max_length=32, blank=True, default='')
    new_status = models.CharField(max_length=32, blank=True, default='')

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscription_actions'
    )
    source = models.CharField(max_length=64, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'subscription_events'
        verbose_name = 'Subscription Event'
        verbose_name_plural = 'Subscription Events'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subscription} -> {self.event_type} at {self.created_at}"


class CustomerOTP(models.Model):
    """
    Secure one-time-password for customer self-service portal login.
    OTP codes are hashed with SHA-256 at rest.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customer_otps')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='otps')

    phone = models.CharField(max_length=32, db_index=True)
    otp_hash = models.CharField(max_length=128, help_text="Cryptographic hash of the 6-digit OTP.")

    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customer_otps'
        verbose_name = 'Customer OTP'
        verbose_name_plural = 'Customer OTPs'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.phone} (expires {self.expires_at})"


class CustomerSubscriptionSettings(models.Model):
    """
    Tenant-scoped subscription lifecycle and self-service configuration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='subscription_settings')

    grace_period_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Minutes customer remains in GRACE before permanent session disconnect."
    )
    otp_expiry_minutes = models.PositiveIntegerField(
        default=5,
        help_text="Validity window for 6-digit SMS OTP."
    )
    otp_resend_cooldown_seconds = models.PositiveIntegerField(
        default=60,
        help_text="Cooldown seconds before requesting a new OTP."
    )

    remind_1day_before = models.BooleanField(
        default=True,
        help_text="Send SMS reminder 24 hours before expiration."
    )
    remind_1hour_before = models.BooleanField(
        default=True,
        help_text="Send SMS reminder 1 hour before expiration."
    )
    remind_at_expiry = models.BooleanField(
        default=True,
        help_text="Send SMS notification at expiration."
    )

    allow_self_service = models.BooleanField(
        default=True,
        help_text="Allow customers to view portal and trigger manual renewals."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_subscription_settings'
        verbose_name = 'Customer Subscription Settings'
        verbose_name_plural = 'Customer Subscription Settings'

    def __str__(self):
        return f"Subscription Settings ({self.company.name})"
