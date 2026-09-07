import uuid
from django.core.exceptions import ValidationError
from django.db import models
from apps.companies.models import Company
from apps.core.security import decrypt_secret, encrypt_secret
from apps.locations.models import Location


class RouterHealthStatus(models.TextChoices):
    ONLINE = 'ONLINE', 'Online'
    OFFLINE = 'OFFLINE', 'Offline'
    DEGRADED = 'DEGRADED', 'Degraded'
    UNREACHABLE = 'UNREACHABLE', 'Unreachable'
    UNKNOWN = 'UNKNOWN', 'Unknown'


class Router(models.Model):
    """
    Physical or logical network appliance / gateway (e.g. MikroTik hAP ac lite, RB4011, CCR, CHR).
    Manages hardware inventory, RouterOS API communication, and hosts hotspot services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='routers'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='routers',
        help_text="Physical location where router is deployed"
    )
    name = models.CharField(max_length=255, help_text="Human label e.g. Kariakoo-Main-GW")
    identity = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="MikroTik system identity (/system identity)"
    )
    vendor = models.CharField(max_length=64, default='MikroTik')
    model = models.CharField(max_length=128, blank=True, default='', help_text="e.g. hAP ac lite, RB4011iGS+")
    serial_number = models.CharField(max_length=128, blank=True, default='', db_index=True)
    
    # Management Access
    management_ip = models.GenericIPAddressField(
        help_text="IP address used for RouterOS API / WinBox management"
    )
    api_port = models.PositiveIntegerField(
        default=8728,
        help_text="RouterOS API port (8728 for plain, 8729 for TLS)"
    )
    use_tls = models.BooleanField(
        default=False,
        help_text="Use RouterOS API-SSL encrypted connection"
    )
    api_username = models.CharField(max_length=128, default='admin')
    api_password_encrypted = models.TextField(
        blank=True,
        default='',
        help_text="Encrypted RouterOS API management password"
    )
    
    # System Telemetry & Firmware
    routeros_version = models.CharField(max_length=64, blank=True, default='', help_text="e.g. 7.15.2")
    architecture = models.CharField(max_length=64, blank=True, default='', help_text="e.g. mipsbe, arm64, x86_64")
    firmware_version = models.CharField(max_length=64, blank=True, default='')
    health_status = models.CharField(
        max_length=32,
        choices=RouterHealthStatus.choices,
        default=RouterHealthStatus.UNKNOWN,
        db_index=True
    )
    last_seen_at = models.DateTimeField(null=True, blank=True)
    system_resources = models.JSONField(
        default=dict,
        blank=True,
        help_text="Latest cached telemetry snapshot (cpu_load, free_memory, uptime, etc.)"
    )
    
    uplink_interface_name = models.CharField(
        max_length=64,
        default='wlan2',
        blank=True,
        help_text="Default upstream station/WAN wireless interface name (e.g. wlan2, ether1)"
    )
    last_health_check_at = models.DateTimeField(null=True, blank=True)
    health_message = models.TextField(blank=True, default='', help_text="Diagnostic message from last health check")
    
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'routers'
        verbose_name = 'Router'
        verbose_name_plural = 'Routers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'location']),
            models.Index(fields=['company', 'health_status']),
            models.Index(fields=['management_ip']),
        ]

    def __str__(self):
        return f"{self.name} ({self.management_ip}) - {self.location.name}"

    @property
    def fallback_management_ip(self) -> str:
        """Fallback LAN gateway IP from hosted hotspot on bridgeLocal (e.g. 10.5.50.1)."""
        hs = self.hotspots.first()
        if hs and hs.gateway_ip:
            return str(hs.gateway_ip)
        return '10.5.50.1'

    @property
    def api_password(self) -> str:
        """Decrypt RouterOS API password from at-rest ciphertext."""
        if not self.api_password_encrypted:
            return ''
        return decrypt_secret(self.api_password_encrypted)

    @api_password.setter
    def api_password(self, value: str):
        """Encrypt RouterOS API password for secure at-rest storage."""
        if value:
            self.api_password_encrypted = encrypt_secret(value)
        else:
            self.api_password_encrypted = ''

    @property
    def has_credentials(self) -> bool:
        """Indicate whether management credentials are configured."""
        return bool(self.api_username and self.api_password_encrypted)

    def clean(self):
        super().clean()
        if self.api_port < 1 or self.api_port > 65535:
            raise ValidationError({'api_port': 'API port must be between 1 and 65535.'})
        if self.location_id and self.company_id and self.location.company_id != self.company_id:
            raise ValidationError({'location': 'Router location must belong to the same company.'})
