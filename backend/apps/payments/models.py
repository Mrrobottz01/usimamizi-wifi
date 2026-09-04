import uuid
from decimal import Decimal

from django.db import models

from apps.companies.models import Company
from apps.core.security import decrypt_secret, encrypt_secret


class PaymentProvider(models.TextChoices):
    SNIPPE = 'SNIPPE', 'Snippe'
    MANUAL = 'MANUAL', 'Manual'


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PurchaseStatus(models.TextChoices):
    CREATED = 'CREATED', 'Created'
    PAYMENT_PENDING = 'PAYMENT_PENDING', 'Payment Pending'
    PAID = 'PAID', 'Paid'
    ENTITLEMENT_CREATED = 'ENTITLEMENT_CREATED', 'Entitlement Created'
    FULFILLED = 'FULFILLED', 'Fulfilled'
    FAILED = 'FAILED', 'Failed'
    EXPIRED = 'EXPIRED', 'Expired'


class WalledGardenEntryType(models.TextChoices):
    DOMAIN = 'DOMAIN', 'Domain (dst-host)'
    IP = 'IP', 'IP Address'
    CIDR = 'CIDR', 'CIDR Subnet'


class WalledGardenPurpose(models.TextChoices):
    PORTAL = 'PORTAL', 'Captive Portal'
    PAYMENT = 'PAYMENT', 'Payment Provider'
    SYSTEM = 'SYSTEM', 'System Infrastructure'
    CUSTOM = 'CUSTOM', 'Custom'


class PaymentProviderConfiguration(models.Model):
    """
    Tenant-scoped payment gateway credentials and preferences.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payment_configs')
    provider = models.CharField(max_length=32, choices=PaymentProvider.choices, default=PaymentProvider.SNIPPE)
    is_enabled = models.BooleanField(default=True)
    environment = models.CharField(max_length=16, default='sandbox', choices=[('sandbox', 'Sandbox'), ('live', 'Live')])
    api_base_url = models.URLField(default='https://api.snippe.sh')
    api_key_encrypted = models.TextField(blank=True, default='', help_text="Encrypted API key for provider")
    webhook_secret_encrypted = models.TextField(blank=True, default='', help_text="Encrypted webhook signature secret")
    default_currency = models.CharField(max_length=8, default='TZS')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_provider_configurations'
        unique_together = ('company', 'provider')
        verbose_name = 'Payment Provider Configuration'

    def __str__(self):
        return f"{self.company.name} - {self.provider} ({'Live' if self.environment == 'live' else 'Sandbox'})"

    @property
    def api_key(self) -> str:
        return decrypt_secret(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value: str):
        self.api_key_encrypted = encrypt_secret(value)

    @property
    def webhook_secret(self) -> str:
        return decrypt_secret(self.webhook_secret_encrypted)

    @webhook_secret.setter
    def webhook_secret(self, value: str):
        self.webhook_secret_encrypted = encrypt_secret(value)


class AccessPurchase(models.Model):
    """
    Order entity tracking customer intent to acquire access via self-service payment.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='access_purchases')
    hotspot = models.ForeignKey('companies.HotspotConfiguration', null=True, blank=True, on_delete=models.SET_NULL, related_name='purchases')
    plan = models.ForeignKey('plans.Plan', on_delete=models.PROTECT, related_name='purchases')
    reference = models.CharField(max_length=64, unique=True, db_index=True, help_text="Customer reference e.g. PUR-20260903-XXXXXX")

    customer_phone = models.CharField(max_length=32, db_index=True, help_text="Customer E.164 phone number")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default='TZS')
    status = models.CharField(max_length=32, choices=PurchaseStatus.choices, default=PurchaseStatus.CREATED, db_index=True)

    entitlement = models.ForeignKey(
        'entitlements.AccessEntitlement',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchases'
    )
    voucher = models.ForeignKey(
        'vouchers.Voucher',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchases'
    )

    client_mac = models.CharField(max_length=32, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'access_purchases'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['customer_phone', 'status']),
            models.Index(fields=['reference']),
        ]

    def __str__(self):
        return f"{self.reference} [{self.status}] - {self.customer_phone} ({self.amount} {self.currency})"


class PaymentTransaction(models.Model):
    """
    Financial transaction log tied to an AccessPurchase and PaymentProvider.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payment_transactions')
    purchase = models.ForeignKey(AccessPurchase, on_delete=models.CASCADE, related_name='transactions')
    provider = models.CharField(max_length=32, choices=PaymentProvider.choices, default=PaymentProvider.SNIPPE)
    provider_reference = models.CharField(max_length=255, blank=True, default='', db_index=True)
    internal_reference = models.CharField(max_length=64, unique=True, db_index=True, help_text="Transaction reference e.g. TXN-20260903-XXXXXX")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='TZS')
    status = models.CharField(max_length=32, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True)

    payment_method = models.CharField(max_length=64, blank=True, default='mobile')
    customer_phone = models.CharField(max_length=32, blank=True, default='')
    checkout_url = models.URLField(max_length=512, blank=True, default='')
    payment_link_url = models.URLField(max_length=512, blank=True, default='')
    raw_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payment_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['provider_reference']),
            models.Index(fields=['internal_reference']),
        ]

    def __str__(self):
        return f"{self.internal_reference} [{self.status}] {self.amount} {self.currency} ({self.provider})"


class PaymentAttempt(models.Model):
    """
    Idempotency and outbound attempt tracking for provider API calls.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, related_name='attempts')
    idempotency_key = models.CharField(max_length=30, db_index=True, help_text="Snippe max 30-char idempotency key")
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_attempts'
        ordering = ['-created_at']


class PaymentWebhookEvent(models.Model):
    """
    Inbound payment webhook audit trail ensuring duplicate-safe idempotency.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32, choices=PaymentProvider.choices, default=PaymentProvider.SNIPPE)
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=128, db_index=True)
    signature = models.CharField(max_length=512, blank=True, default='')
    payload = models.JSONField(default=dict)
    is_processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_webhook_events'
        ordering = ['-created_at']


class HotspotWalledGardenEntry(models.Model):
    """
    HotSpot pre-authentication allowlist entries for MikroTik HotSpot walled garden.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='walled_garden_entries')
    hotspot = models.ForeignKey('companies.HotspotConfiguration', null=True, blank=True, on_delete=models.CASCADE, related_name='walled_garden_entries')
    entry_type = models.CharField(max_length=32, choices=WalledGardenEntryType.choices, default=WalledGardenEntryType.DOMAIN)
    host = models.CharField(max_length=255, blank=True, default='', help_text="Domain name e.g. api.snippe.sh")
    address = models.CharField(max_length=255, blank=True, default='', help_text="IP or CIDR for walled-garden ip")
    protocol = models.CharField(max_length=16, blank=True, default='')
    port = models.CharField(max_length=16, blank=True, default='')
    purpose = models.CharField(max_length=32, choices=WalledGardenPurpose.choices, default=WalledGardenPurpose.PAYMENT)
    description = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hotspot_walled_garden_entries'
        ordering = ['purpose', 'host', 'address']

    def __str__(self):
        target = self.host if self.entry_type == WalledGardenEntryType.DOMAIN else self.address
        return f"[{self.purpose}] {self.entry_type}: {target}"
