from rest_framework import serializers
from ..models import AntiTetheringPolicy, IPv6Policy


class AntiTetheringPolicySerializer(serializers.ModelSerializer):
    hotspot_id = serializers.UUIDField(source='hotspot.id', read_only=True)
    hotspot_name = serializers.CharField(source='hotspot.name', read_only=True)

    class Meta:
        model = AntiTetheringPolicy
        fields = [
            'id',
            'hotspot_id',
            'hotspot_name',
            'enabled',
            'max_devices',
            'simultaneous_sessions',
            'ttl_lock_enabled',
            'ttl_lock_value',
            'detect_ttl_63',
            'detect_ttl_127',
            'strict_mode',
            'ipv6_policy',
            'last_synced_at',
            'last_router_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'hotspot_id',
            'hotspot_name',
            'last_synced_at',
            'last_router_status',
            'created_at',
            'updated_at',
        ]

    def validate_ttl_lock_value(self, value):
        if value < 1 or value > 255:
            raise serializers.ValidationError("TTL value must be between 1 and 255.")
        return value

    def validate_max_devices(self, value):
        if value < 1:
            raise serializers.ValidationError("Maximum devices must be at least 1.")
        return value

    def validate_simultaneous_sessions(self, value):
        if value < 1:
            raise serializers.ValidationError("Simultaneous sessions must be at least 1.")
        return value
