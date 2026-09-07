from rest_framework import serializers

from apps.locations.models import Location
from apps.routers.models import Router, RouterHealthStatus


class RouterSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    has_credentials = serializers.BooleanField(read_only=True)
    hotspot_count = serializers.SerializerMethodField()
    fallback_management_ip = serializers.CharField(read_only=True)

    class Meta:
        model = Router
        fields = [
            'id',
            'company',
            'location',
            'location_name',
            'name',
            'identity',
            'vendor',
            'model',
            'serial_number',
            'management_ip',
            'fallback_management_ip',
            'api_port',
            'use_tls',
            'api_username',
            'has_credentials',
            'routeros_version',
            'architecture',
            'firmware_version',
            'health_status',
            'health_message',
            'last_seen_at',
            'last_health_check_at',
            'system_resources',
            'uplink_interface_name',
            'is_active',
            'hotspot_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'company',
            'location_name',
            'fallback_management_ip',
            'has_credentials',
            'routeros_version',
            'architecture',
            'firmware_version',
            'health_status',
            'health_message',
            'last_seen_at',
            'last_health_check_at',
            'system_resources',
            'hotspot_count',
            'created_at',
            'updated_at',
        ]

    def get_hotspot_count(self, obj) -> int:
        return obj.hotspots.count() if hasattr(obj, 'hotspots') else 0


class RouterCreateSerializer(serializers.ModelSerializer):
    api_password = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')

    class Meta:
        model = Router
        fields = [
            'id',
            'location',
            'name',
            'identity',
            'vendor',
            'model',
            'serial_number',
            'management_ip',
            'api_port',
            'use_tls',
            'api_username',
            'api_password',
            'uplink_interface_name',
            'is_active',
        ]

    def validate_location(self, value):
        company = self.context.get('company')
        if company and value.company_id != company.id:
            raise serializers.ValidationError("Location does not belong to the selected company.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('api_password', '')
        company = self.context.get('company')
        router = Router(company=company, **validated_data)
        if password:
            router.api_password = password
        router.save()
        return router


class RouterCredentialsSerializer(serializers.Serializer):
    api_username = serializers.CharField(required=True, max_length=128)
    api_password = serializers.CharField(required=True, write_only=True, max_length=128)
    api_port = serializers.IntegerField(required=False, min_value=1, max_value=65535)
    use_tls = serializers.BooleanField(required=False)
