import uuid

from django.db import models

from apps.companies.models import Company


class NotificationChannel(models.TextChoices):
    SMS = 'SMS', 'SMS'
    EMAIL = 'EMAIL', 'Email'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'


class NotificationStatus(models.TextChoices):
    QUEUED = 'QUEUED', 'Queued'
    SENDING = 'SENDING', 'Sending'
    SENT = 'SENT', 'Sent'
    DELIVERED = 'DELIVERED', 'Delivered'
    FAILED = 'FAILED', 'Failed'


class SMSProviderType(models.TextChoices):
    BEEM = 'BEEM', 'Beem Africa'
    NEXTSMS = 'NEXTSMS', 'NextSMS Tanzania'
    RAFIKISMS = 'RAFIKISMS', 'RafikiSMS'
    MOCK = 'MOCK', 'Mock SMS Provider'


class NotificationTemplate(models.Model):
    """
    Notification template per channel and company.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='notification_templates')
    code = models.CharField(max_length=64, help_text="Template code e.g. VOUCHER_CREATED")
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices, default=NotificationChannel.SMS)
    language = models.CharField(max_length=8, default='en')
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_templates'
        unique_together = ('company', 'code', 'channel', 'language')

    def __str__(self):
        return f"{self.code} [{self.channel}] ({self.language})"


class NotificationProviderConfiguration(models.Model):
    """
    Multi-provider configuration settings for SMS gateways.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='provider_configs')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, help_text="Provider code e.g. beem, nextsms, rafikisms, mock")
    provider_type = models.CharField(max_length=32, choices=SMSProviderType.choices, default=SMSProviderType.MOCK)
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices, default=NotificationChannel.SMS)

    priority = models.PositiveIntegerField(default=10, help_text="Routing priority (lower number = higher priority)")
    is_active = models.BooleanField(default=True)

    base_url = models.CharField(max_length=255, blank=True, default='')
    sender_id = models.CharField(max_length=32, blank=True, default='', help_text="Configured fallback/default sender ID")
    default_sender_id = models.CharField(max_length=32, blank=True, default='', help_text="Default synced sender ID chosen by operator")

    supports_delivery_receipts = models.BooleanField(default=True)
    settings_json = models.JSONField(default=dict, blank=True)
    encrypted_credentials = models.JSONField(default=dict, blank=True, help_text="Encrypted or secure provider credentials")

    last_sender_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_provider_configurations'
        ordering = ['priority', 'created_at']

    def __str__(self):
        return f"{self.name} ({self.code}) - Priority {self.priority}"


class SMSProviderSenderID(models.Model):
    """
    Cached, provider-discovered sender IDs available for a specific gateway configuration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_configuration = models.ForeignKey(
        NotificationProviderConfiguration,
        on_delete=models.CASCADE,
        related_name='available_sender_ids'
    )
    sender_id = models.CharField(max_length=32, help_text="Alphanumeric sender ID e.g. USIMAMIZI")
    external_id = models.CharField(max_length=128, blank=True, default='', help_text="Provider external sender ID UUID/ref")
    display_name = models.CharField(max_length=128, blank=True, default='')
    status = models.CharField(max_length=32, default='active')
    is_available = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_provider_sender_ids'
        unique_together = ('provider_configuration', 'sender_id')
        ordering = ['-is_default', 'sender_id']

    def __str__(self):
        return f"{self.sender_id} ({self.provider_configuration.code}) [{'DEFAULT' if self.is_default else self.status}]"


class TenantSMSSenderPreference(models.Model):
    """
    Tenant-specific sender ID selection override per provider.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='sms_sender_preferences')
    provider_code = models.CharField(max_length=64)
    sender_id = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenant_sms_sender_preferences'
        unique_together = ('company', 'provider_code')

    def __str__(self):
        return f"{self.company.name} -> {self.provider_code}: {self.sender_id}"


class NotificationMessage(models.Model):
    """
    Logical notification message record.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='notification_messages')
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices, default=NotificationChannel.SMS)
    recipient = models.CharField(max_length=255)
    phone_normalized = models.CharField(max_length=32, blank=True, default='')

    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    voucher = models.ForeignKey('vouchers.Voucher', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    rendered_content = models.TextField()

    status = models.CharField(max_length=16, choices=NotificationStatus.choices, default=NotificationStatus.QUEUED, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notification_messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.channel}] {self.recipient} - {self.status}"


class DeliveryAttemptStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'
    PENDING = 'PENDING', 'Pending'


class NotificationDeliveryAttempt(models.Model):
    """
    Audit log of individual provider delivery attempts for multi-provider failover tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='delivery_attempts')
    notification_message = models.ForeignKey(NotificationMessage, on_delete=models.CASCADE, related_name='attempts')
    provider_code = models.CharField(max_length=64)
    sender_id = models.CharField(max_length=64, blank=True, default='', help_text="Sender ID snapshot used for this delivery attempt")

    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=DeliveryAttemptStatus.choices, default=DeliveryAttemptStatus.PENDING)

    provider_reference = models.CharField(max_length=255, blank=True, default='')
    provider_status = models.CharField(max_length=64, blank=True, default='')

    failure_category = models.CharField(max_length=64, blank=True, default='')
    failure_code = models.CharField(max_length=64, blank=True, default='')
    failure_reason = models.TextField(blank=True, default='')

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'notification_delivery_attempts'
        ordering = ['attempt_number']

    def __str__(self):
        return f"Attempt #{self.attempt_number} ({self.provider_code} / {self.sender_id}) - {self.status}"
