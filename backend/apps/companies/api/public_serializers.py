from rest_framework import serializers

from apps.companies.models import HotspotConfiguration


class PublicHotspotConfigSerializer(serializers.ModelSerializer):
    """
    Safe public branding tokens returned to captive portal clients.
    Excludes internal company IDs, NAS secrets, and credentials.
    """
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = HotspotConfiguration
        fields = [
            'id',
            'name',
            'slug',
            'ssid',
            'company_name',
            'brand_name',
            'headline',
            'welcome_text',
            'primary_color',
            'logo_url',
            'support_phone',
            'terms_url',
            'privacy_url',
            'default_language',
            'router_login_url',
            'is_active',
        ]


class PublicVoucherSubmitSerializer(serializers.Serializer):
    voucher_code = serializers.CharField(max_length=64, required=True, trim_whitespace=True)
    customer_phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    language = serializers.CharField(max_length=8, required=False, default='EN')


class AdminHotspotSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for admin settings page to customize branding tokens.
    """
    class Meta:
        model = HotspotConfiguration
        fields = [
            'id',
            'name',
            'slug',
            'ssid',
            'brand_name',
            'headline',
            'welcome_text',
            'primary_color',
            'logo_url',
            'support_phone',
            'terms_url',
            'privacy_url',
            'default_language',
            'router_login_url',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
