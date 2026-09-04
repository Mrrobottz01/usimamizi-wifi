from rest_framework import serializers

from apps.payments.models import (
    AccessPurchase,
    HotspotWalledGardenEntry,
    PaymentProviderConfiguration,
    PaymentTransaction,
    WalledGardenEntryType,
)
from apps.plans.models import Plan


class PublicPlanSerializer(serializers.ModelSerializer):
    """
    Publicly visible Wi-Fi plan details for captive portal checkout.
    """
    class Meta:
        model = Plan
        fields = [
            'id',
            'name',
            'description',
            'price',
            'currency',
            'validity_mode',
            'duration_value',
            'duration_unit',
            'download_speed_kbps',
            'upload_speed_kbps',
            'data_limit_bytes',
            'max_devices',
            'simultaneous_sessions',
        ]


class InitiatePurchaseSerializer(serializers.Serializer):
    """
    Customer input when initiating a self-service package purchase.
    """
    plan_id = serializers.UUIDField(required=True)
    customer_phone = serializers.CharField(max_length=32, required=True)
    client_mac = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    ip_address = serializers.IPAddressField(required=False, allow_null=True, default=None)


class PublicPurchaseStatusSerializer(serializers.ModelSerializer):
    """
    Safe public status response polled by the captive portal browser.
    """
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    voucher_code = serializers.SerializerMethodField()
    checkout_url = serializers.SerializerMethodField()

    class Meta:
        model = AccessPurchase
        fields = [
            'reference',
            'status',
            'amount',
            'currency',
            'customer_phone',
            'plan_name',
            'voucher_code',
            'checkout_url',
            'error_message',
            'created_at',
            'completed_at',
        ]

    def get_voucher_code(self, obj) -> str:
        if obj.voucher:
            return obj.voucher.display_code
        if obj.entitlement:
            return obj.entitlement.reference
        return ""

    def get_checkout_url(self, obj) -> str:
        latest_txn = obj.transactions.first()
        return latest_txn.checkout_url if latest_txn else ""


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Full financial transaction serializer for admin dashboard.
    """
    purchase_reference = serializers.CharField(source='purchase.reference', read_only=True)
    plan_name = serializers.CharField(source='purchase.plan.name', read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            'id',
            'purchase',
            'purchase_reference',
            'plan_name',
            'provider',
            'provider_reference',
            'internal_reference',
            'amount',
            'currency',
            'status',
            'payment_method',
            'customer_phone',
            'checkout_url',
            'created_at',
            'completed_at',
            'failed_at',
            'updated_at',
        ]


class AccessPurchaseSerializer(serializers.ModelSerializer):
    """
    Full purchase order serializer for admin dashboard.
    """
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    hotspot_name = serializers.CharField(source='hotspot.name', read_only=True, default='')
    voucher_code = serializers.SerializerMethodField()
    entitlement_reference = serializers.SerializerMethodField()

    class Meta:
        model = AccessPurchase
        fields = [
            'id',
            'reference',
            'hotspot',
            'hotspot_name',
            'plan',
            'plan_name',
            'customer_phone',
            'amount',
            'currency',
            'status',
            'voucher_code',
            'entitlement_reference',
            'client_mac',
            'ip_address',
            'error_message',
            'created_at',
            'completed_at',
        ]

    def get_voucher_code(self, obj) -> str:
        return obj.voucher.display_code if obj.voucher else ""

    def get_entitlement_reference(self, obj) -> str:
        return obj.entitlement.reference if obj.entitlement else ""


class PaymentSettingsSerializer(serializers.ModelSerializer):
    """
    Tenant payment gateway configuration with masked secret display.
    """
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    webhook_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_key_masked = serializers.SerializerMethodField()
    webhook_secret_masked = serializers.SerializerMethodField()

    class Meta:
        model = PaymentProviderConfiguration
        fields = [
            'id',
            'provider',
            'is_enabled',
            'environment',
            'api_base_url',
            'default_currency',
            'api_key',
            'webhook_secret',
            'api_key_masked',
            'webhook_secret_masked',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'provider', 'created_at', 'updated_at']

    def get_api_key_masked(self, obj) -> str:
        raw = obj.api_key
        if not raw:
            return "Not Configured"
        if len(raw) <= 8:
            return "••••••••"
        return f"{raw[:4]}••••••••{raw[-4:]}"

    def get_webhook_secret_masked(self, obj) -> str:
        raw = obj.webhook_secret
        if not raw:
            return "Not Configured"
        if len(raw) <= 8:
            return "••••••••"
        return f"{raw[:4]}••••••••{raw[-4:]}"

    def update(self, instance, validated_data):
        api_key = validated_data.pop('api_key', None)
        webhook_secret = validated_data.pop('webhook_secret', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if api_key is not None and api_key.strip():
            instance.api_key = api_key.strip()
        if webhook_secret is not None and webhook_secret.strip():
            instance.webhook_secret = webhook_secret.strip()

        instance.save()
        return instance


class WalledGardenEntrySerializer(serializers.ModelSerializer):
    """
    Walled garden entry CRUD serializer.
    """
    class Meta:
        model = HotspotWalledGardenEntry
        fields = [
            'id',
            'hotspot',
            'entry_type',
            'host',
            'address',
            'protocol',
            'port',
            'purpose',
            'description',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        entry_type = attrs.get('entry_type')
        host = attrs.get('host', '').strip()
        address = attrs.get('address', '').strip()

        if entry_type == WalledGardenEntryType.DOMAIN and not host:
            raise serializers.ValidationError({"host": "Host domain is required for DOMAIN entries."})
        elif entry_type in [WalledGardenEntryType.IP, WalledGardenEntryType.CIDR] and not address:
            raise serializers.ValidationError({"address": "IP Address or CIDR is required for IP entries."})
        return attrs


class ApplyPresetSerializer(serializers.Serializer):
    preset_name = serializers.CharField(required=True)
    hotspot_id = serializers.UUIDField(required=False, allow_null=True)
