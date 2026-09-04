import uuid

from django.conf import settings
from django.db import models

from apps.companies.models import Company
from apps.plans.models import Plan, ValidityMode
from apps.vouchers.models import Voucher


class EntitlementSourceType(models.TextChoices):
    VOUCHER = 'VOUCHER', 'Voucher'
    MANUAL = 'MANUAL', 'Manual Grant'
    PAYMENT = 'PAYMENT', 'Direct Payment'
    PROMOTION = 'PROMOTION', 'Promotion'
    ADMIN = 'ADMIN', 'Administrator'


class EntitlementStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    EXPIRED = 'EXPIRED', 'Expired'
    REVOKED = 'REVOKED', 'Revoked'


class AccessEntitlement(models.Model):
    """
    Core domain model representing a customer's legal/commercial right to access the network.
    FreeRADIUS in future Phase 4/5 consumes this entity for authorization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='entitlements')
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_entitlements'
    )
    voucher = models.OneToOneField(
        Voucher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entitlement',
        help_text="One-to-one constraint: A voucher can yield maximum 1 access entitlement."
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='entitlements')

    source_type = models.CharField(max_length=32, choices=EntitlementSourceType.choices, default=EntitlementSourceType.VOUCHER)
    status = models.CharField(max_length=32, choices=EntitlementStatus.choices, default=EntitlementStatus.PENDING, db_index=True)
    reference = models.CharField(max_length=64, unique=True, db_index=True, help_text="Human-readable entitlement code e.g. ENT-20260830-XXXXXX")

    # Time Bounds & Lifecycles
    activated_at = models.DateTimeField(null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    validity_mode = models.CharField(max_length=32, default=ValidityMode.CONTINUOUS)

    # Bandwidth Limits (Rate Shaping Snapshot)
    download_speed_kbps = models.PositiveIntegerField(null=True, blank=True)
    upload_speed_kbps = models.PositiveIntegerField(null=True, blank=True)

    # Quota & Consumption
    data_limit_bytes = models.BigIntegerField(null=True, blank=True)
    data_used_bytes = models.BigIntegerField(default=0)
    usage_time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    usage_time_used_seconds = models.PositiveIntegerField(default=0)

    # Device & Concurrency Limits
    max_devices = models.PositiveIntegerField(default=1)
    simultaneous_sessions = models.PositiveIntegerField(default=1)

    # Timeouts
    idle_timeout_seconds = models.PositiveIntegerField(null=True, blank=True)
    session_timeout_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Immutable Commercial Snapshot
    plan_snapshot = models.JSONField(default=dict, help_text="Frozen snapshot of Plan commercial properties at creation.")

    # Suspension Metadata
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suspended_entitlements'
    )
    suspension_reason = models.TextField(blank=True, default='')

    # Revocation Metadata
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revoked_entitlements'
    )
    revocation_reason = models.TextField(blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_entitlements'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'access_entitlements'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=models.Q(data_used_bytes__gte=0), name='check_data_used_non_negative'),
            models.CheckConstraint(condition=models.Q(usage_time_used_seconds__gte=0), name='check_usage_time_used_non_negative'),
            models.CheckConstraint(condition=models.Q(max_devices__gte=1), name='check_max_devices_gte_1'),
            models.CheckConstraint(condition=models.Q(simultaneous_sessions__gte=1), name='check_simultaneous_sessions_gte_1'),
        ]

    def __str__(self):
        return f"{self.reference} ({self.plan.name}) - {self.status}"

    @property
    def remaining_data_bytes(self):
        if self.data_limit_bytes is None:
            return None
        return max(0, self.data_limit_bytes - self.data_used_bytes)

    @property
    def remaining_usage_time_seconds(self):
        if self.usage_time_limit_seconds is None:
            return None
        return max(0, self.usage_time_limit_seconds - self.usage_time_used_seconds)
