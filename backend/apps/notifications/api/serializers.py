from rest_framework import serializers

from ..models import (
    NotificationDeliveryAttempt,
    NotificationMessage,
    NotificationProviderConfiguration,
    SMSProviderSenderID,
    TenantSMSSenderPreference,
)
from ..services.history_services import mask_phone_number


class SMSProviderSenderIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSProviderSenderID
        fields = [
            'id',
            'sender_id',
            'external_id',
            'display_name',
            'status',
            'is_available',
            'is_default',
            'last_synced_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_synced_at', 'created_at', 'updated_at']


class NotificationProviderConfigSerializer(serializers.ModelSerializer):
    available_sender_ids = SMSProviderSenderIDSerializer(many=True, read_only=True)
    sender_ids_count = serializers.SerializerMethodField()

    class Meta:
        model = NotificationProviderConfiguration
        fields = [
            'id',
            'name',
            'code',
            'provider_type',
            'channel',
            'priority',
            'is_active',
            'base_url',
            'sender_id',
            'default_sender_id',
            'supports_delivery_receipts',
            'last_sender_sync_at',
            'available_sender_ids',
            'sender_ids_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sender_sync_at', 'available_sender_ids', 'sender_ids_count']

    def get_sender_ids_count(self, obj) -> int:
        return obj.available_sender_ids.filter(is_available=True).count()


class TenantSMSSenderPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSMSSenderPreference
        fields = ['id', 'provider_code', 'sender_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationDeliveryAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDeliveryAttempt
        fields = [
            'id',
            'provider_code',
            'sender_id',
            'attempt_number',
            'status',
            'provider_reference',
            'provider_status',
            'failure_category',
            'failure_code',
            'failure_reason',
            'started_at',
            'completed_at',
        ]


class NotificationMessageSerializer(serializers.ModelSerializer):
    attempts = NotificationDeliveryAttemptSerializer(many=True, read_only=True)

    class Meta:
        model = NotificationMessage
        fields = [
            'id',
            'channel',
            'recipient',
            'phone_normalized',
            'rendered_content',
            'status',
            'created_at',
            'sent_at',
            'delivered_at',
            'failed_at',
            'attempts',
        ]


class SMSHistoryListSerializer(serializers.ModelSerializer):
    recipient = serializers.SerializerMethodField()
    phone_normalized = serializers.SerializerMethodField()
    recipient_masked = serializers.SerializerMethodField()
    message_type = serializers.SerializerMethodField()
    provider_used = serializers.SerializerMethodField()
    sender_id = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    provider_reference = serializers.SerializerMethodField()
    voucher_id = serializers.SerializerMethodField()
    voucher_code = serializers.SerializerMethodField()
    voucher_batch_id = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()

    class Meta:
        model = NotificationMessage
        fields = [
            'id',
            'recipient_masked',
            'recipient',
            'phone_normalized',
            'channel',
            'message_type',
            'status',
            'provider_used',
            'sender_id',
            'attempt_count',
            'provider_reference',
            'voucher_id',
            'voucher_code',
            'voucher_batch_id',
            'plan_name',
            'created_at',
            'sent_at',
            'delivered_at',
            'failed_at',
        ]

    def get_recipient(self, obj) -> str:
        request = self.context.get('request')
        if request and request.user and (request.user.is_staff or request.user.has_perm('notifications.view_recipient')):
            return obj.recipient
        return mask_phone_number(obj.recipient)

    def get_phone_normalized(self, obj) -> str:
        request = self.context.get('request')
        if request and request.user and (request.user.is_staff or request.user.has_perm('notifications.view_recipient')):
            return obj.phone_normalized
        return mask_phone_number(obj.phone_normalized)

    def get_recipient_masked(self, obj) -> str:
        return mask_phone_number(obj.phone_normalized or obj.recipient)

    def get_message_type(self, obj) -> str:
        if obj.template:
            return obj.template.code
        elif obj.voucher_id:
            return 'VOUCHER_SMS'
        return 'DIRECT_SMS'

    def _get_last_attempt(self, obj):
        attempts = getattr(obj, '_prefetched_attempts', None)
        if attempts is None:
            attempts = list(obj.attempts.all())
        return attempts[-1] if attempts else None

    def get_provider_used(self, obj) -> str:
        last = self._get_last_attempt(obj)
        return last.provider_code if last else ''

    def get_sender_id(self, obj) -> str:
        last = self._get_last_attempt(obj)
        return last.sender_id if last else ''

    def get_attempt_count(self, obj) -> int:
        attempts = getattr(obj, '_prefetched_attempts', None)
        if attempts is None:
            return obj.attempts.count()
        return len(attempts)

    def get_provider_reference(self, obj) -> str:
        last = self._get_last_attempt(obj)
        return last.provider_reference if last else ''

    def get_voucher_id(self, obj):
        return str(obj.voucher_id) if obj.voucher_id else None

    def get_voucher_code(self, obj):
        return obj.voucher.display_code if obj.voucher else None

    def get_voucher_batch_id(self, obj):
        return str(obj.voucher.batch_id) if obj.voucher and obj.voucher.batch_id else None

    def get_plan_name(self, obj):
        return obj.voucher.plan.name if obj.voucher and obj.voucher.plan else None


class SMSHistoryDetailSerializer(serializers.ModelSerializer):
    attempts = NotificationDeliveryAttemptSerializer(many=True, read_only=True)
    recipient_masked = serializers.SerializerMethodField()
    message_type = serializers.SerializerMethodField()
    voucher_id = serializers.SerializerMethodField()
    voucher_code = serializers.SerializerMethodField()
    voucher_batch_id = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()

    class Meta:
        model = NotificationMessage
        fields = [
            'id',
            'recipient_masked',
            'recipient',
            'phone_normalized',
            'channel',
            'message_type',
            'rendered_content',
            'status',
            'can_retry',
            'voucher_id',
            'voucher_code',
            'voucher_batch_id',
            'plan_name',
            'created_at',
            'queued_at',
            'sent_at',
            'delivered_at',
            'failed_at',
            'attempts',
        ]

    def get_recipient_masked(self, obj) -> str:
        return mask_phone_number(obj.phone_normalized or obj.recipient)

    def get_message_type(self, obj) -> str:
        if obj.template:
            return obj.template.code
        elif obj.voucher_id:
            return 'VOUCHER_SMS'
        return 'DIRECT_SMS'

    def get_voucher_id(self, obj):
        return str(obj.voucher_id) if obj.voucher_id else None

    def get_voucher_code(self, obj):
        return obj.voucher.display_code if obj.voucher else None

    def get_voucher_batch_id(self, obj):
        return str(obj.voucher.batch_id) if obj.voucher and obj.voucher.batch_id else None

    def get_plan_name(self, obj):
        return obj.voucher.plan.name if obj.voucher and obj.voucher.plan else None

    def get_can_retry(self, obj) -> bool:
        return obj.status == 'FAILED'


class TestSMSSerializer(serializers.Serializer):
    recipient_phone = serializers.CharField(required=True)
    provider_code = serializers.CharField(required=False, allow_blank=True, default='')
    sender_id = serializers.CharField(required=False, allow_blank=True, default='')
    message_text = serializers.CharField(required=False, default='Usimamizi Wi-Fi: Test SMS delivery verified successfully.')
