from rest_framework import serializers

from apps.plans.models import Plan
from ..models import (
    Customer,
    CustomerDevice,
    CustomerSubscriptionSettings,
    Subscription,
    SubscriptionEvent,
    SubscriptionStatus,
)


class CustomerDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDevice
        fields = [
            'id',
            'mac_address',
            'device_name',
            'device_type',
            'is_trusted',
            'is_blocked',
            'first_seen_at',
            'last_seen_at',
            'created_at',
        ]
        read_only_fields = ['id', 'first_seen_at', 'last_seen_at', 'created_at']


class SubscriptionEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, default='')

    class Meta:
        model = SubscriptionEvent
        fields = [
            'id',
            'event_type',
            'old_status',
            'new_status',
            'actor_email',
            'source',
            'metadata',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    customer_phone = serializers.CharField(source='customer.normalized_phone', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_price = serializers.DecimalField(source='plan.price', max_digits=12, decimal_places=2, read_only=True)
    plan_currency = serializers.CharField(source='plan.currency', read_only=True)
    hotspot_name = serializers.CharField(source='hotspot.ssid', read_only=True, default='')
    remaining_seconds = serializers.IntegerField(read_only=True)
    is_valid_now = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id',
            'company_id',
            'customer_id',
            'customer_phone',
            'customer_name',
            'plan_id',
            'plan_name',
            'plan_price',
            'plan_currency',
            'hotspot_id',
            'hotspot_name',
            'status',
            'started_at',
            'current_period_start',
            'current_period_end',
            'grace_period_end',
            'remaining_seconds',
            'is_valid_now',
            'renewal_mode',
            'source',
            'plan_snapshot',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'company_id',
            'customer_phone',
            'customer_name',
            'plan_name',
            'plan_price',
            'plan_currency',
            'remaining_seconds',
            'is_valid_now',
            'created_at',
            'updated_at',
        ]


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    devices_count = serializers.SerializerMethodField()
    active_subscription = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id',
            'company_id',
            'phone',
            'normalized_phone',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'status',
            'language',
            'notes',
            'devices_count',
            'active_subscription',
            'total_spent',
            'last_seen_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'company_id',
            'normalized_phone',
            'full_name',
            'devices_count',
            'active_subscription',
            'total_spent',
            'last_seen_at',
            'created_at',
            'updated_at',
        ]

    def get_devices_count(self, obj) -> int:
        return obj.devices.count()

    def get_active_subscription(self, obj):
        sub = obj.subscriptions.filter(
            status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE]
        ).order_by('-current_period_end').first()
        if sub:
            return {
                'id': str(sub.id),
                'plan_name': sub.plan.name if sub.plan else '',
                'status': sub.status,
                'current_period_end': sub.current_period_end.isoformat() if sub.current_period_end else None,
                'remaining_seconds': sub.remaining_seconds,
            }
        return None

    def get_total_spent(self, obj) -> str:
        # Sum completed payments for this customer's normalized phone
        from apps.payments.models import PaymentStatus, PaymentTransaction
        total = PaymentTransaction.objects.filter(
            company_id=obj.company_id,
            customer_phone=obj.normalized_phone,
            status=PaymentStatus.COMPLETED,
        ).values_list('amount', flat=True)
        return str(sum(total)) if total else '0.00'


class CustomerSubscriptionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerSubscriptionSettings
        fields = [
            'id',
            'grace_period_minutes',
            'otp_expiry_minutes',
            'otp_resend_cooldown_seconds',
            'remind_1day_before',
            'remind_1hour_before',
            'remind_at_expiry',
            'allow_self_service',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
