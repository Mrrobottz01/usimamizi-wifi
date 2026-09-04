from rest_framework import serializers

from ..models import AccessEntitlement
from ..services.entitlement_services import is_entitlement_authorizable


class AccessEntitlementListSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()
    plan_code = serializers.SerializerMethodField()
    voucher_code = serializers.SerializerMethodField()
    voucher_id = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    remaining_data_bytes = serializers.ReadOnlyField()
    remaining_usage_time_seconds = serializers.ReadOnlyField()

    class Meta:
        model = AccessEntitlement
        fields = [
            'id',
            'reference',
            'status',
            'source_type',
            'plan_id',
            'plan_name',
            'plan_code',
            'voucher_id',
            'voucher_code',
            'customer_email',
            'activated_at',
            'valid_from',
            'expires_at',
            'validity_mode',
            'download_speed_kbps',
            'upload_speed_kbps',
            'data_limit_bytes',
            'data_used_bytes',
            'remaining_data_bytes',
            'usage_time_limit_seconds',
            'usage_time_used_seconds',
            'remaining_usage_time_seconds',
            'max_devices',
            'simultaneous_sessions',
            'created_at',
        ]

    def get_plan_name(self, obj) -> str:
        return obj.plan.name if obj.plan else obj.plan_snapshot.get('plan_name', '')

    def get_plan_code(self, obj) -> str:
        return obj.plan.code if obj.plan else obj.plan_snapshot.get('plan_code', '')

    def get_voucher_code(self, obj):
        return obj.voucher.display_code if obj.voucher else None

    def get_voucher_id(self, obj):
        return str(obj.voucher.id) if obj.voucher else None

    def get_customer_email(self, obj):
        return obj.customer.email if obj.customer else None


class AccessEntitlementDetailSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()
    plan_code = serializers.SerializerMethodField()
    voucher_code = serializers.SerializerMethodField()
    voucher_id = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()
    suspended_by_email = serializers.SerializerMethodField()
    revoked_by_email = serializers.SerializerMethodField()
    is_authorizable = serializers.SerializerMethodField()
    authorization_status = serializers.SerializerMethodField()
    remaining_data_bytes = serializers.ReadOnlyField()
    remaining_usage_time_seconds = serializers.ReadOnlyField()

    class Meta:
        model = AccessEntitlement
        fields = [
            'id',
            'reference',
            'status',
            'source_type',
            'plan_id',
            'plan_name',
            'plan_code',
            'voucher_id',
            'voucher_code',
            'customer_email',
            'activated_at',
            'valid_from',
            'expires_at',
            'validity_mode',
            'download_speed_kbps',
            'upload_speed_kbps',
            'data_limit_bytes',
            'data_used_bytes',
            'remaining_data_bytes',
            'usage_time_limit_seconds',
            'usage_time_used_seconds',
            'remaining_usage_time_seconds',
            'max_devices',
            'simultaneous_sessions',
            'idle_timeout_seconds',
            'session_timeout_seconds',
            'plan_snapshot',
            'suspended_at',
            'suspended_by_email',
            'suspension_reason',
            'revoked_at',
            'revoked_by_email',
            'revocation_reason',
            'created_by_email',
            'is_authorizable',
            'authorization_status',
            'created_at',
            'updated_at',
        ]

    def get_plan_name(self, obj) -> str:
        return obj.plan.name if obj.plan else obj.plan_snapshot.get('plan_name', '')

    def get_plan_code(self, obj) -> str:
        return obj.plan.code if obj.plan else obj.plan_snapshot.get('plan_code', '')

    def get_voucher_code(self, obj):
        return obj.voucher.display_code if obj.voucher else None

    def get_voucher_id(self, obj):
        return str(obj.voucher.id) if obj.voucher else None

    def get_customer_email(self, obj):
        return obj.customer.email if obj.customer else None

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    def get_suspended_by_email(self, obj):
        return obj.suspended_by.email if obj.suspended_by else None

    def get_revoked_by_email(self, obj):
        return obj.revoked_by.email if obj.revoked_by else None

    def get_is_authorizable(self, obj) -> bool:
        auth_ok, _ = is_entitlement_authorizable(obj)
        return auth_ok

    def get_authorization_status(self, obj) -> str:
        _, reason = is_entitlement_authorizable(obj)
        return reason


class ManualGrantSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField(required=True)
    reason = serializers.CharField(required=True, min_length=3, max_length=255)
    customer_id = serializers.UUIDField(required=False, allow_null=True)


class SuspendEntitlementSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class RevokeEntitlementSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3, max_length=255)
