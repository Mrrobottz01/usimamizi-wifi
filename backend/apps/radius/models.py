import uuid

from django.db import models

from apps.companies.models import Company
from apps.core.security import decrypt_secret, encrypt_secret
from apps.entitlements.models import AccessEntitlement


class RadiusClient(models.Model):
    """
    NAS / Router representation authorized to interact with FreeRADIUS AAA.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='radius_clients'
    )
    name = models.CharField(max_length=255)
    nas_ip = models.GenericIPAddressField(db_index=True)
    nas_identifier = models.CharField(max_length=255, blank=True, default='', db_index=True)
    shared_secret_encrypted = models.TextField(default='', blank=True, help_text="Encrypted shared RADIUS secret key")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'radius_clients'
        verbose_name = 'RADIUS Client'
        verbose_name_plural = 'RADIUS Clients'
        unique_together = ('company', 'nas_ip')

    def __str__(self):
        return f"{self.name} ({self.nas_ip}) - {self.company.name}"

    @property
    def shared_secret(self) -> str:
        return decrypt_secret(self.shared_secret_encrypted)

    @shared_secret.setter
    def shared_secret(self, value: str):
        self.shared_secret_encrypted = encrypt_secret(value)


class EntitlementDevice(models.Model):
    """
    Physical client device MAC address bound to an AccessEntitlement for max_devices enforcement.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entitlement = models.ForeignKey(
        AccessEntitlement,
        on_delete=models.CASCADE,
        related_name='devices'
    )
    mac_address = models.CharField(max_length=32, db_index=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'entitlement_devices'
        unique_together = ('entitlement', 'mac_address')
        ordering = ['-first_seen_at']

    def __str__(self):
        return f"{self.mac_address} -> {self.entitlement.reference}"


class AccountingPacketType(models.TextChoices):
    START = 'Start', 'Start'
    INTERIM = 'Interim-Update', 'Interim Update'
    STOP = 'Stop', 'Stop'


class RadiusAccountingLog(models.Model):
    """
    Immutable raw protocol evidence stream of all received RADIUS accounting packets.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_logs'
    )
    radius_client = models.ForeignKey(
        RadiusClient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_logs'
    )
    entitlement = models.ForeignKey(
        AccessEntitlement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_logs'
    )

    session_id = models.CharField(max_length=255, db_index=True)
    username = models.CharField(max_length=255, db_index=True)
    nas_ip = models.GenericIPAddressField(db_index=True)
    nas_identifier = models.CharField(max_length=255, blank=True, default='')
    mac_address = models.CharField(max_length=32, blank=True, default='')
    framed_ip = models.GenericIPAddressField(null=True, blank=True)

    packet_type = models.CharField(max_length=30, choices=AccountingPacketType.choices)

    input_octets = models.BigIntegerField(default=0)
    output_octets = models.BigIntegerField(default=0)
    input_gigawords = models.PositiveIntegerField(default=0)
    output_gigawords = models.PositiveIntegerField(default=0)

    total_input_bytes = models.BigIntegerField(default=0)
    total_output_bytes = models.BigIntegerField(default=0)

    session_time = models.IntegerField(default=0, help_text="Session duration in seconds")
    terminate_cause = models.CharField(max_length=255, blank=True, default='')

    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'radius_accounting_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.packet_type}] {self.username} - {self.session_id} ({self.session_time}s)"
