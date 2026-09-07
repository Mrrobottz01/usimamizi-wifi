import re
import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from apps.companies.models import Company


class LocationStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    MAINTENANCE = 'MAINTENANCE', 'Maintenance'


class SiteType(models.TextChoices):
    BRANCH = 'BRANCH', 'Branch'
    HOTEL = 'HOTEL', 'Hotel'
    RESTAURANT = 'RESTAURANT', 'Restaurant'
    CAFE = 'CAFE', 'Café'
    BUS_TERMINAL = 'BUS_TERMINAL', 'Bus Terminal'
    MALL = 'MALL', 'Shopping Mall'
    OFFICE = 'OFFICE', 'Office'
    PUBLIC_SITE = 'PUBLIC_SITE', 'Public Site'
    OTHER = 'OTHER', 'Other'


def generate_location_code(company: Company, name: str = '') -> str:
    """
    Generate a deterministic, collision-safe, human-readable location code
    scoped to the company (e.g. LOC-DAR-001, LOC-MAIN-001).
    """
    prefix = 'LOC'
    clean_name = re.sub(r'[^A-Za-z0-9]', '', name).upper()[:3] if name else 'SITE'
    base = f"{prefix}-{clean_name}"
    
    # Find next sequence number
    existing_codes = set(
        Location.objects.filter(company=company, code__startswith=base)
        .values_list('code', flat=True)
    )
    for seq in range(1, 1000):
        candidate = f"{base}-{seq:03d}"
        if candidate not in existing_codes:
            return candidate
    return f"{base}-{uuid.uuid4().hex[:4].upper()}"


class Location(models.Model):
    """
    Physical deployment venue or business site (e.g. Kariakoo Branch, Mbezi Beach Site).
    Provides spatial, operational, and geographic context for routers and hotspots.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=64,
        help_text="Company-unique short code for location identifier (e.g. LOC-DAR-001)"
    )
    region = models.CharField(max_length=128, blank=True, default='', help_text="e.g. Dar es Salaam, Arusha, Mwanza")
    district = models.CharField(max_length=128, blank=True, default='', help_text="e.g. Ilala, Kinondoni, Arusha City")
    address = models.TextField(blank=True, default='', help_text="Street address or physical landmark")
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=64, default='Africa/Dar_es_Salaam')
    
    status = models.CharField(
        max_length=32,
        choices=LocationStatus.choices,
        default=LocationStatus.ACTIVE,
        db_index=True
    )
    site_type = models.CharField(
        max_length=32,
        choices=SiteType.choices,
        default=SiteType.OTHER,
        blank=True,
        db_index=True,
        help_text="Operational deployment classification (e.g. BRANCH, HOTEL, MALL)"
    )
    operating_hours = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text="Operating schedule e.g. 24/7, 08:00 - 22:00"
    )
    installation_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the venue or infrastructure was commissioned"
    )
    external_reference = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text="ERP, CRM, or client billing code"
    )
    contact_person = models.CharField(max_length=255, blank=True, default='')
    contact_phone = models.CharField(max_length=32, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'locations'
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'code'],
                name='unique_company_location_code'
            )
        ]
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'name']),
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.company.name}"

    def clean(self):
        super().clean()
        if self.latitude is not None and not (Decimal('-90.0') <= self.latitude <= Decimal('90.0')):
            raise ValidationError({'latitude': 'Latitude must be between -90.0 and +90.0 degrees.'})
        if self.longitude is not None and not (Decimal('-180.0') <= self.longitude <= Decimal('180.0')):
            raise ValidationError({'longitude': 'Longitude must be between -180.0 and +180.0 degrees.'})
        if self.timezone:
            import zoneinfo
            if self.timezone not in zoneinfo.available_timezones():
                raise ValidationError({'timezone': f"'{self.timezone}' is not a valid IANA timezone name."})

    def save(self, *args, **kwargs):
        if not self.code and self.company_id:
            self.code = generate_location_code(self.company, self.name)
        super().save(*args, **kwargs)
