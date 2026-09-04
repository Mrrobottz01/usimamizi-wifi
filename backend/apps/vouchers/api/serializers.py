from rest_framework import serializers

from apps.plans.api.serializers import PlanSerializer

from ..models import Voucher, VoucherBatch


class VoucherSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_code = serializers.CharField(source='plan.code', read_only=True)
    batch_reference = serializers.CharField(source='batch.reference', read_only=True)
    entitlement_id = serializers.SerializerMethodField()
    entitlement_reference = serializers.SerializerMethodField()

    class Meta:
        model = Voucher
        fields = [
            'id',
            'company_id',
            'batch_id',
            'batch_reference',
            'plan_id',
            'plan_name',
            'plan_code',
            'display_code',
            'status',
            'distribution_state',
            'export_status',
            'recipient_phone',
            'reserved_at',
            'expires_at',
            'redeemed_at',
            'redeemed_by_customer',
            'entitlement_id',
            'entitlement_reference',
            'revoked_at',
            'revocation_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'display_code', 'status', 'redeemed_at', 'revoked_at', 'created_at', 'updated_at']

    def get_entitlement_id(self, obj):
        try:
            return str(obj.entitlement.id) if hasattr(obj, 'entitlement') and obj.entitlement else None
        except Exception:
            return None

    def get_entitlement_reference(self, obj):
        try:
            return obj.entitlement.reference if hasattr(obj, 'entitlement') and obj.entitlement else None
        except Exception:
            return None


class VoucherBatchSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, default='')

    available_count = serializers.SerializerMethodField()
    reserved_count = serializers.SerializerMethodField()
    redeemed_count = serializers.SerializerMethodField()
    revoked_count = serializers.SerializerMethodField()
    expired_count = serializers.SerializerMethodField()

    class Meta:
        model = VoucherBatch
        fields = [
            'id',
            'company_id',
            'plan',
            'reference',
            'label',
            'notes',
            'quantity',
            'distribution_mode',
            'export_status',
            'expires_at',
            'created_by_email',
            'available_count',
            'reserved_count',
            'redeemed_count',
            'revoked_count',
            'expired_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'reference', 'created_at', 'updated_at']

    def get_available_count(self, obj):
        return obj.vouchers.filter(status='AVAILABLE').count()

    def get_reserved_count(self, obj):
        return obj.vouchers.filter(status='RESERVED').count()

    def get_redeemed_count(self, obj):
        return obj.vouchers.filter(status='REDEEMED').count()

    def get_revoked_count(self, obj):
        return obj.vouchers.filter(status='REVOKED').count()

    def get_expired_count(self, obj):
        return obj.vouchers.filter(status='EXPIRED').count()


class GenerateBatchSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, max_value=5000, required=True)
    label = serializers.CharField(allow_blank=True, default='')
    notes = serializers.CharField(allow_blank=True, default='')
    distribution_mode = serializers.CharField(allow_blank=True, default='UNSOLD')
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class RevokeVoucherSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, default='')


class SendVoucherSMSSerializer(serializers.Serializer):
    recipient_phone = serializers.CharField(required=True)


class ReserveVoucherSerializer(serializers.Serializer):
    customer_phone = serializers.CharField(allow_blank=True, default='')
    recipient_phone = serializers.CharField(allow_blank=True, default='')
    distribution_state = serializers.CharField(allow_blank=True, default='')

