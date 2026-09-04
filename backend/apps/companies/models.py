import uuid

from django.conf import settings
from django.db import models


class CompanyStatus(models.TextChoices):
    TRIAL = 'TRIAL', 'Trial'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    legal_name = models.CharField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    country = models.CharField(max_length=2, default='TZ')
    currency = models.CharField(max_length=3, default='TZS')
    timezone = models.CharField(max_length=64, default='Africa/Dar_es_Salaam')
    status = models.CharField(
        max_length=20,
        choices=CompanyStatus.choices,
        default=CompanyStatus.TRIAL,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'companies'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']

    def __str__(self):
        return self.name


class CompanyMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_memberships'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'company_memberships'
        unique_together = ('company', 'user')
        verbose_name = 'Company Membership'
        verbose_name_plural = 'Company Memberships'

    def __str__(self):
        return f"{self.user.email} -> {self.company.name}"


class HotspotConfiguration(models.Model):
    """
    Tenant-scoped HotSpot portal and branding configuration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='hotspots'
    )
    name = models.CharField(max_length=255, default='Main Wi-Fi HotSpot')
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    ssid = models.CharField(max_length=128, default='Usimamizi-WiFi-Lab')
    is_active = models.BooleanField(default=True, db_index=True)

    # Tenant Branding Tokens
    brand_name = models.CharField(max_length=255, blank=True, default='')
    headline = models.CharField(max_length=255, blank=True, default='Welcome to High-Speed Wi-Fi')
    welcome_text = models.TextField(blank=True, default='Enter your access voucher code below to start browsing.')
    primary_color = models.CharField(max_length=32, default='#2563eb', blank=True)
    logo_url = models.URLField(max_length=512, blank=True, default='')
    support_phone = models.CharField(max_length=64, blank=True, default='')
    terms_url = models.URLField(max_length=512, blank=True, default='')
    privacy_url = models.URLField(max_length=512, blank=True, default='')
    default_language = models.CharField(max_length=8, default='EN', choices=[('EN', 'English'), ('SW', 'Kiswahili')])

    # Router Handoff URL (e.g. http://10.5.50.1/login or $(link-login-only))
    router_login_url = models.CharField(max_length=255, default='http://10.5.50.1/login')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hotspot_configurations'
        verbose_name = 'HotSpot Configuration'
        verbose_name_plural = 'HotSpot Configurations'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.slug}) - {self.company.name}"


class RouterUplinkProfile(models.Model):
    """
    Saved upstream Wi-Fi / WAN profile for MikroTik station interface (e.g. Home Airtel, Office Vodacom).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='uplink_profiles'
    )
    name = models.CharField(max_length=128, help_text="e.g. Home Airtel 5G, Office Vodacom")
    ssid = models.CharField(max_length=128)
    password = models.CharField(max_length=128, blank=True, default='')
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'router_uplink_profiles'
        verbose_name = 'Router Uplink Profile'
        verbose_name_plural = 'Router Uplink Profiles'
        ordering = ['-is_active', 'name']

    def __str__(self):
        return f"{self.name} ({self.ssid}) - {'ACTIVE' if self.is_active else 'SAVED'}"

