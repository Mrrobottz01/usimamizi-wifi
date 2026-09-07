from rest_framework import serializers

from ..models import HotspotSession, SessionDisconnectRequest


class SessionDisconnectRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.SerializerMethodField()
    nas_ip = serializers.SerializerMethodField()

    class Meta:
        model = SessionDisconnectRequest
        fields = [
            'id',
            'hotspot_session_id',
            'trigger_type',
            'status',
            'reason',
            'requested_by_email',
            'nas_ip',
            'requested_at',
            'sent_at',
            'acknowledged_at',
            'failed_at',
            'attempt_count',
            'response_code',
            'response_message',
            'last_error',
            'created_at',
        ]

    def get_requested_by_email(self, obj) -> str:
        return obj.requested_by.email if obj.requested_by else 'System Automation'

    def get_nas_ip(self, obj) -> str:
        return obj.radius_client.nas_ip if obj.radius_client else ''


class ManualDisconnectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=True, allow_blank=False)


class HotspotSessionSerializer(serializers.ModelSerializer):
    entitlement_reference = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    radius_client_name = serializers.SerializerMethodField()
    total_bytes = serializers.ReadOnlyField()
    latest_disconnect_status = serializers.SerializerMethodField()
    device_name = serializers.SerializerMethodField()

    class Meta:
        model = HotspotSession
        fields = [
            'id',
            'acct_session_id',
            'username',
            'mac_address',
            'ip_address',
            'device_name',
            'status',
            'entitlement_id',
            'entitlement_reference',
            'plan_name',
            'radius_client_name',
            'started_at',
            'last_accounting_at',
            'ended_at',
            'input_bytes',
            'output_bytes',
            'total_bytes',
            'session_seconds',
            'termination_reason',
            'latest_disconnect_status',
            'created_at',
        ]

    def get_entitlement_reference(self, obj) -> str:
        return obj.entitlement.reference if obj.entitlement else ''

    def get_plan_name(self, obj) -> str:
        return obj.entitlement.plan.name if obj.entitlement and obj.entitlement.plan else ''

    def get_radius_client_name(self, obj) -> str:
        return obj.radius_client.name if obj.radius_client else 'Direct / Default NAS'

    def get_latest_disconnect_status(self, obj) -> str:
        latest = obj.disconnect_requests.first()
        return latest.status if latest else ''

    def get_device_name(self, obj) -> str:
        if obj.device_name:
            return obj.device_name
        if obj.device and obj.device.device_name:
            return obj.device.device_name
        return ''
