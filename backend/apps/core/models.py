import uuid
from django.db import models
from django.utils import timezone


class ServiceName(models.TextChoices):
    FREERADIUS = 'FREERADIUS', 'FreeRADIUS Daemon'
    ROUTER_GATEWAY = 'ROUTER_GATEWAY', 'MikroTik Router'
    DATABASE = 'DATABASE', 'Primary Database'
    SMS_GATEWAY = 'SMS_GATEWAY', 'SMS Gateway'


class IncidentStatus(models.TextChoices):
    HEALTHY = 'HEALTHY', 'Healthy'
    DEGRADED = 'DEGRADED', 'Degraded'
    DOWN = 'DOWN', 'Down'


class SystemWatchdogConfig(models.Model):
    """
    Global and per-tenant watchdog configuration for monitoring and alerting.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='watchdog_configs'
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Master toggle for watchdog probes and alerts."
    )
    alert_phone_numbers = models.CharField(
        max_length=255,
        default='+255712345678',
        help_text="Comma-separated phone numbers in E.164 format to receive alert SMS (e.g. +255712345678,+255687654321)"
    )
    alert_cooldown_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Minutes to suppress repeat SMS alerts during an active outage to prevent burning SMS credits."
    )
    check_interval_seconds = models.PositiveIntegerField(
        default=60,
        help_text="Recommended polling interval for background daemon."
    )
    radius_host = models.CharField(
        max_length=128,
        default='127.0.0.1',
        help_text="Host/IP of the FreeRADIUS server."
    )
    radius_auth_port = models.PositiveIntegerField(
        default=1812,
        help_text="FreeRADIUS authentication UDP port."
    )
    radius_secret = models.CharField(
        max_length=128,
        default='testing123',
        help_text="RADIUS shared secret for testing auth challenges."
    )
    notify_on_recovery = models.BooleanField(
        default=True,
        help_text="Send a follow-up SMS when a downed service recovers."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_system_watchdog_configs'
        verbose_name = 'System Watchdog Configuration'
        verbose_name_plural = 'System Watchdog Configurations'

    def __str__(self):
        target = self.company.name if self.company else "GLOBAL PLATFORM"
        return f"Watchdog Config [{target}] (Enabled={self.is_enabled})"


class ServiceIncident(models.Model):
    """
    Audit record of service degradation or outage events.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='service_incidents'
    )
    service_name = models.CharField(
        max_length=32,
        choices=ServiceName.choices,
        db_index=True
    )
    service_identifier = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text="Identifier for instance, e.g. '127.0.0.1:1812' or Router IP '192.168.1.107'"
    )
    status = models.CharField(
        max_length=16,
        choices=IncidentStatus.choices,
        default=IncidentStatus.DOWN,
        db_index=True
    )
    error_message = models.TextField(blank=True, default='')
    detected_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    alert_sent_at = models.DateTimeField(null=True, blank=True)
    recovery_alert_sent_at = models.DateTimeField(null=True, blank=True)
    alert_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'core_service_incidents'
        ordering = ['-detected_at']

    def __str__(self):
        return f"[{self.service_name} - {self.service_identifier}] {self.status} (detected: {self.detected_at})"
