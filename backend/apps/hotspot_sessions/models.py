import uuid

from django.db import models
from django.utils import timezone

from apps.accounts.models import User
from apps.companies.models import Company
from apps.entitlements.models import AccessEntitlement


class SessionStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    STOPPED = 'STOPPED', 'Stopped'
    STALE = 'STALE', 'Stale'


class SessionDisconnectTrigger(models.TextChoices):
    MANUAL = 'MANUAL', 'Manual Admin Action'
    ENTITLEMENT_SUSPENDED = 'ENTITLEMENT_SUSPENDED', 'Entitlement Suspended'
    ENTITLEMENT_REVOKED = 'ENTITLEMENT_REVOKED', 'Entitlement Revoked'
    DATA_QUOTA_EXHAUSTED = 'DATA_QUOTA_EXHAUSTED', 'Data Quota Exhausted'
    USAGE_TIME_EXHAUSTED = 'USAGE_TIME_EXHAUSTED', 'Usage Time Exhausted'
    ADMIN_SECURITY_ACTION = 'ADMIN_SECURITY_ACTION', 'Admin Security Action'


class DisconnectStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SENDING = 'SENDING', 'Sending'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    FAILED = 'FAILED', 'Failed'
    TIMEOUT = 'TIMEOUT', 'Timeout'
    CANCELLED = 'CANCELLED', 'Cancelled'


class HotspotSession(models.Model):
    """
    Observed physical network connection session between a client device and a MikroTik NAS.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='hotspot_sessions')
    entitlement = models.ForeignKey(AccessEntitlement, on_delete=models.CASCADE, related_name='sessions')
    radius_client = models.ForeignKey('radius.RadiusClient', on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')

    acct_session_id = models.CharField(max_length=255, db_index=True)
    username = models.CharField(max_length=255, db_index=True)
    mac_address = models.CharField(max_length=32, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    status = models.CharField(max_length=32, choices=SessionStatus.choices, default=SessionStatus.ACTIVE, db_index=True)

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_accounting_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    input_bytes = models.BigIntegerField(default=0, help_text="Total client upload bytes in session")
    output_bytes = models.BigIntegerField(default=0, help_text="Total client download bytes in session")
    session_seconds = models.PositiveIntegerField(default=0, help_text="Elapsed session connection time in seconds")

    termination_reason = models.CharField(max_length=128, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hotspot_sessions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['entitlement', 'status']),
            models.Index(fields=['radius_client', 'acct_session_id']),
        ]

    def __str__(self):
        return f"[{self.status}] {self.username} ({self.mac_address}) - {self.session_seconds}s"

    @property
    def total_bytes(self) -> int:
        return self.input_bytes + self.output_bytes


class SessionDisconnectRequest(models.Model):
    """
    RADIUS Disconnect-Request (RFC 3576 / RFC 5176) tracking and audit evidence.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='disconnect_requests')
    hotspot_session = models.ForeignKey(HotspotSession, on_delete=models.CASCADE, related_name='disconnect_requests')
    radius_client = models.ForeignKey('radius.RadiusClient', on_delete=models.SET_NULL, null=True, blank=True, related_name='disconnect_requests')

    trigger_type = models.CharField(
        max_length=64,
        choices=SessionDisconnectTrigger.choices,
        default=SessionDisconnectTrigger.MANUAL,
        db_index=True
    )
    status = models.CharField(
        max_length=32,
        choices=DisconnectStatus.choices,
        default=DisconnectStatus.PENDING,
        db_index=True
    )
    reason = models.CharField(max_length=255, blank=True, default='')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='session_disconnects_requested')

    requested_at = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    attempt_count = models.PositiveIntegerField(default=0)
    response_code = models.CharField(max_length=64, blank=True, default='')
    response_message = models.TextField(blank=True, default='')
    last_error = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'session_disconnect_requests'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['hotspot_session', 'status']),
            models.Index(fields=['requested_at']),
        ]

    def __str__(self):
        return f"Disconnect [{self.status}] {self.hotspot_session.username} ({self.trigger_type})"
