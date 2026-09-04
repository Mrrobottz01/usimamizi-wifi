import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.companies.models import Company


class DurationUnit(models.TextChoices):
    MINUTES = 'MINUTES', 'Minutes'
    HOURS = 'HOURS', 'Hours'
    DAYS = 'DAYS', 'Days'
    WEEKS = 'WEEKS', 'Weeks'
    MONTHS = 'MONTHS', 'Months'


class ValidityMode(models.TextChoices):
    CONTINUOUS = 'CONTINUOUS', 'Continuous (Clock Time)'
    USAGE_TIME = 'USAGE_TIME', 'Usage Time (Active Consumption)'
    CALENDAR = 'CALENDAR', 'Calendar (Fixed End Date)'


class Plan(models.Model):
    """
    SaaS Commercial Internet Access Plan definition.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='plans'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, help_text="Company-unique short code for plan identifier")
    description = models.TextField(blank=True, default='')

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price in specified currency"
    )
    currency = models.CharField(max_length=3, default='TZS')

    duration_value = models.PositiveIntegerField(default=1)
    duration_unit = models.CharField(max_length=16, choices=DurationUnit.choices, default=DurationUnit.HOURS)
    validity_mode = models.CharField(max_length=16, choices=ValidityMode.choices, default=ValidityMode.CONTINUOUS)

    download_speed_kbps = models.PositiveIntegerField(null=True, blank=True, help_text="Download bandwidth limit in Kbps")
    upload_speed_kbps = models.PositiveIntegerField(null=True, blank=True, help_text="Upload bandwidth limit in Kbps")

    data_limit_bytes = models.BigIntegerField(null=True, blank=True, help_text="Total data limit in bytes")

    max_devices = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    simultaneous_sessions = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    idle_timeout_seconds = models.PositiveIntegerField(null=True, blank=True)
    session_timeout_seconds = models.PositiveIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'plans'
        ordering = ['sort_order', 'name']
        unique_together = ('company', 'code')

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.price} {self.currency}"
