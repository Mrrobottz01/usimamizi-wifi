import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.security import encrypt_secret, decrypt_secret


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

    @property
    def default_hotspot(self):
        """Return the designated default active hotspot for the company."""
        return self.hotspots.filter(is_default=True, is_active=True).first() or \
               self.hotspots.filter(is_default=True).first() or \
               self.hotspots.filter(is_active=True).first()


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
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hotspots',
        help_text="Physical venue/location of this hotspot"
    )
    router = models.ForeignKey(
        'routers.Router',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hotspots',
        help_text="Router hosting this hotspot service"
    )
    interface_name = models.CharField(
        max_length=64,
        blank=True,
        default='bridgeLocal',
        help_text="Router interface or bridge e.g. bridgeLocal, vlan10"
    )
    server_name = models.CharField(
        max_length=64,
        blank=True,
        default='hotspot1',
        help_text="MikroTik /ip hotspot server name"
    )
    gateway_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Customer default gateway IP on hotspot network (e.g. 10.5.50.1)"
    )
    subnet_mask = models.CharField(
        max_length=32,
        blank=True,
        default='255.255.255.0',
        help_text="Subnet mask or CIDR e.g. 255.255.255.0 or /24"
    )
    ssid = models.CharField(max_length=128, default='Usimamizi-WiFi-Lab')
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Primary/default hotspot for the company"
    )
    plans = models.ManyToManyField(
        'plans.Plan',
        blank=True,
        related_name='hotspots',
        help_text="Specific plans available on this hotspot. If empty, all active company plans are offered."
    )

    # Tenant Branding Tokens
    brand_name = models.CharField(max_length=255, blank=True, default='')
    headline = models.CharField(max_length=255, blank=True, default='Welcome to High-Speed Wi-Fi')
    welcome_text = models.TextField(blank=True, default='Enter your access voucher code below to start browsing.')
    primary_color = models.CharField(max_length=32, default='#2563eb', blank=True)
    logo_url = models.URLField(max_length=512, blank=True, default='')
    support_phone = models.CharField(max_length=64, blank=True, default='')
    terms_url = models.URLField(max_length=512, blank=True, default='')
    privacy_url = models.URLField(max_length=512, blank=True, default='')
    default_language = models.CharField(max_length=8, default='SW', choices=[('EN', 'English'), ('SW', 'Kiswahili')])

    # Router Handoff URL (e.g. http://10.5.50.1/login or $(link-login-only))
    router_login_url = models.CharField(max_length=255, default='http://10.5.50.1/login')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hotspot_configurations'
        verbose_name = 'HotSpot Configuration'
        verbose_name_plural = 'HotSpot Configurations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'router']),
            models.Index(fields=['company', 'location']),
            models.Index(fields=['company', 'slug']),
            models.Index(fields=['company', 'is_default']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['company'],
                condition=models.Q(is_default=True),
                name='unique_default_hotspot_per_company'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.slug}) - {self.company.name}"

    def clean(self):
        super().clean()
        if self.location_id and self.company_id and self.location.company_id != self.company_id:
            raise ValidationError({'location': 'Hotspot location must belong to the same company.'})
        if self.router_id and self.company_id and self.router.company_id != self.company_id:
            raise ValidationError({'router': 'Hotspot router must belong to the same company.'})
        if self.location_id and self.router_id and self.router.location_id and self.router.location_id != self.location_id:
            raise ValidationError({'location': 'Hotspot location must match the hosting router location.'})


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
    router = models.ForeignKey(
        'routers.Router',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uplink_profiles',
        help_text="Optional router this uplink profile belongs to"
    )
    name = models.CharField(max_length=128, help_text="e.g. Home Airtel 5G, Office Vodacom")
    ssid = models.CharField(max_length=128)
    password_encrypted = models.TextField(blank=True, default='', help_text="Encrypted upstream Wi-Fi password")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def password(self) -> str:
        """Decrypt upstream Wi-Fi password from at-rest ciphertext."""
        if not self.password_encrypted:
            return ''
        try:
            return decrypt_secret(self.password_encrypted)
        except Exception:
            return ''

    @password.setter
    def password(self, val: str):
        """Encrypt upstream Wi-Fi password for secure at-rest storage."""
        if val:
            self.password_encrypted = encrypt_secret(val)
        else:
            self.password_encrypted = ''

    @property
    def has_password(self) -> bool:
        return bool(self.password_encrypted)

    class Meta:
        db_table = 'router_uplink_profiles'
        verbose_name = 'Router Uplink Profile'
        verbose_name_plural = 'Router Uplink Profiles'
        ordering = ['-is_active', 'name']

    def __str__(self):
        return f"{self.name} ({self.ssid}) - {'ACTIVE' if self.is_active else 'SAVED'}"


class IPv6Policy(models.TextChoices):
    DISABLED = 'DISABLED', 'Disabled (Not Configured)'
    BLOCK_IPV6 = 'BLOCK_IPV6', 'Block IPv6 Traffic'
    FUTURE_MANAGED = 'FUTURE_MANAGED', 'Future Managed'


class AntiTetheringPolicy(models.Model):
    """
    Tenant-scoped policy for controlling hotspot tethering / Wi-Fi sharing.
    Manages MikroTik TTL locks, forwarded TTL drops, and AAA device boundaries.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='anti_tethering_policies'
    )
    hotspot = models.OneToOneField(
        HotspotConfiguration,
        on_delete=models.CASCADE,
        related_name='anti_tethering_policy'
    )

    enabled = models.BooleanField(
        default=True,
        help_text="Master toggle to enforce Anti-Tethering protection."
    )

    # AAA & Device Boundaries (synced with plan / entitlement guidelines)
    max_devices = models.PositiveIntegerField(
        default=1,
        help_text="Maximum authorized physical devices per entitlement."
    )
    simultaneous_sessions = models.PositiveIntegerField(
        default=1,
        help_text="Maximum concurrent RADIUS sessions per voucher/account."
    )

    # IPv4 Downstream TTL Lock (Mangle postrouting set:1)
    ttl_lock_enabled = models.BooleanField(
        default=True,
        help_text="Enforce IPv4 downstream TTL lock to prevent tethered forwarding."
    )
    ttl_lock_value = models.PositiveIntegerField(
        default=1,
        help_text="Target TTL value for downstream client packets (standard is 1)."
    )

    # Forwarded Client Traffic Detection (Filter forward drops)
    detect_ttl_63 = models.BooleanField(
        default=True,
        help_text="Drop forwarded client packets from Android/iOS/macOS (TTL 63)."
    )
    detect_ttl_127 = models.BooleanField(
        default=True,
        help_text="Drop forwarded client packets from Windows (TTL 127)."
    )

    # Advanced Controls
    strict_mode = models.BooleanField(
        default=False,
        help_text="Strict enforcement mode (experimental)."
    )
    ipv6_policy = models.CharField(
        max_length=32,
        choices=IPv6Policy.choices,
        default=IPv6Policy.DISABLED
    )

    # Synchronization state
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_router_status = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'anti_tethering_policies'
        verbose_name = 'Anti-Tethering Policy'
        verbose_name_plural = 'Anti-Tethering Policies'
        ordering = ['-created_at']

    def __str__(self):
        status_str = "ENABLED" if self.enabled else "DISABLED"
        return f"Anti-Tethering ({self.hotspot.name}) - {status_str}"

