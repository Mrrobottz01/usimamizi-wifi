import uuid

from django.conf import settings
from django.db import models

from apps.companies.models import Company
from apps.plans.models import Plan


class VoucherStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Available'
    RESERVED = 'RESERVED', 'Reserved'
    REDEEMED = 'REDEEMED', 'Redeemed'
    EXPIRED = 'EXPIRED', 'Expired'
    REVOKED = 'REVOKED', 'Revoked'


class VoucherExportStatus(models.TextChoices):
    NOT_EXPORTED = 'NOT_EXPORTED', 'Not Exported (Central SaaS)'
    EXPORTED_ROUTEROS = 'EXPORTED_ROUTEROS', 'Exported to RouterOS (Local Fallback)'


class VoucherDistributionState(models.TextChoices):
    UNSOLD = 'UNSOLD', 'Unsold'
    SOLD = 'SOLD', 'Sold'
    GIVEN_FREE = 'GIVEN_FREE', 'Given Free'
    PROMOTIONAL = 'PROMOTIONAL', 'Promotional'
    INTERNAL_TEST = 'INTERNAL_TEST', 'Internal Test'


class VoucherBatch(models.Model):
    """
    Batch grouping of generated vouchers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='voucher_batches'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='voucher_batches'
    )
    reference = models.CharField(max_length=64, help_text="Unique batch reference e.g. VB-202608-000001")
    label = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, default='', help_text="Operator notes or distribution details")
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional batch issuance expiration date")

    distribution_mode = models.CharField(
        max_length=32,
        choices=VoucherDistributionState.choices,
        default=VoucherDistributionState.UNSOLD,
        db_index=True
    )
    export_status = models.CharField(
        max_length=32,
        choices=VoucherExportStatus.choices,
        default=VoucherExportStatus.NOT_EXPORTED,
        db_index=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_voucher_batches'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'voucher_batches'
        ordering = ['-created_at']
        unique_together = ('company', 'reference')

    def __str__(self):
        return f"Batch {self.reference} - {self.quantity} x {self.plan.name}"


class Voucher(models.Model):
    """
    Individual Wi-Fi Access Voucher.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='vouchers'
    )
    batch = models.ForeignKey(
        VoucherBatch,
        on_delete=models.CASCADE,
        related_name='vouchers'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='vouchers'
    )

    display_code = models.CharField(max_length=32, db_index=True, help_text="Human readable voucher code e.g. K7PM-4XQ9")
    code_hash = models.CharField(max_length=64, db_index=True, help_text="SHA256 hash of voucher code for secure lookup")

    status = models.CharField(
        max_length=16,
        choices=VoucherStatus.choices,
        default=VoucherStatus.AVAILABLE,
        db_index=True
    )

    distribution_state = models.CharField(
        max_length=32,
        choices=VoucherDistributionState.choices,
        default=VoucherDistributionState.UNSOLD,
        db_index=True
    )
    export_status = models.CharField(
        max_length=32,
        choices=VoucherExportStatus.choices,
        default=VoucherExportStatus.NOT_EXPORTED,
        db_index=True
    )

    expires_at = models.DateTimeField(null=True, blank=True, help_text="Issuance expiry date")
    recipient_phone = models.CharField(max_length=32, blank=True, default='', db_index=True)

    reserved_at = models.DateTimeField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    redeemed_by_customer = models.CharField(max_length=64, blank=True, default='')

    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revoked_vouchers'
    )
    revocation_reason = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vouchers'
        ordering = ['-created_at']
        unique_together = ('company', 'display_code')

    def __str__(self):
        return f"Voucher {self.display_code} [{self.status}]"
