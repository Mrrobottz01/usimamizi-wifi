import zoneinfo
from decimal import Decimal
from typing import Any, Dict
from rest_framework import serializers

from apps.locations.models import Location, LocationStatus, SiteType, generate_location_code
from apps.locations.services.location_services import calculate_location_network_health
from apps.routers.models import Router, RouterHealthStatus
from apps.companies.models import HotspotConfiguration
from apps.hotspot_sessions.models import HotspotSession


class LocationListSerializer(serializers.ModelSerializer):
    router_count = serializers.IntegerField(read_only=True, default=0)
    online_router_count = serializers.IntegerField(read_only=True, default=0)
    degraded_router_count = serializers.IntegerField(read_only=True, default=0)
    hotspot_count = serializers.IntegerField(read_only=True, default=0)
    active_hotspot_count = serializers.IntegerField(read_only=True, default=0)
    active_session_count = serializers.IntegerField(read_only=True, default=0)
    network_health = serializers.SerializerMethodField()
    last_network_update_at = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            'id',
            'name',
            'code',
            'region',
            'district',
            'address',
            'status',
            'site_type',
            'is_active',
            'router_count',
            'online_router_count',
            'degraded_router_count',
            'hotspot_count',
            'active_hotspot_count',
            'active_session_count',
            'network_health',
            'last_network_update_at',
            'created_at',
            'updated_at',
        ]

    def get_network_health(self, obj) -> str:
        # If annotated counts exist on obj, compute directly
        rc = getattr(obj, 'router_count', None)
        if rc is not None:
            if rc == 0:
                return 'UNKNOWN'
            online = getattr(obj, 'online_router_count', 0)
            if online == rc:
                return 'HEALTHY'
            elif online > 0:
                return 'DEGRADED'
            elif (getattr(obj, 'degraded_router_count', 0) > 0 or getattr(obj, 'unreachable_router_count', 0) > 0):
                return 'OFFLINE'
            return 'UNKNOWN'
        health, _ = calculate_location_network_health(obj)
        return health

    def get_last_network_update_at(self, obj) -> Any:
        _, summary = calculate_location_network_health(obj)
        return summary.get('last_network_update_at')


class LocationDetailSerializer(serializers.ModelSerializer):
    router_count = serializers.SerializerMethodField()
    online_router_count = serializers.SerializerMethodField()
    degraded_router_count = serializers.SerializerMethodField()
    hotspot_count = serializers.SerializerMethodField()
    active_hotspot_count = serializers.SerializerMethodField()
    active_session_count = serializers.SerializerMethodField()
    network_health = serializers.SerializerMethodField()
    last_network_update_at = serializers.SerializerMethodField()
    network_summary = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            'id',
            'company',
            'name',
            'code',
            'region',
            'district',
            'address',
            'latitude',
            'longitude',
            'timezone',
            'status',
            'site_type',
            'operating_hours',
            'installation_date',
            'external_reference',
            'contact_person',
            'contact_phone',
            'notes',
            'is_active',
            'router_count',
            'online_router_count',
            'degraded_router_count',
            'hotspot_count',
            'active_hotspot_count',
            'active_session_count',
            'network_health',
            'last_network_update_at',
            'network_summary',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'company', 'created_at', 'updated_at']

    def _get_health_summary(self, obj) -> Dict[str, Any]:
        if not hasattr(self, '_health_cache'):
            self._health_cache = {}
        if obj.id not in self._health_cache:
            health, summary = calculate_location_network_health(obj)
            summary['network_health'] = health
            self._health_cache[obj.id] = summary
        return self._health_cache[obj.id]

    def get_router_count(self, obj) -> int:
        if hasattr(obj, 'router_count'):
            return obj.router_count
        return obj.routers.count()

    def get_online_router_count(self, obj) -> int:
        if hasattr(obj, 'online_router_count'):
            return obj.online_router_count
        return obj.routers.filter(is_active=True, health_status=RouterHealthStatus.ONLINE).count()

    def get_degraded_router_count(self, obj) -> int:
        if hasattr(obj, 'degraded_router_count'):
            return obj.degraded_router_count
        return obj.routers.filter(is_active=True, health_status=RouterHealthStatus.DEGRADED).count()

    def get_hotspot_count(self, obj) -> int:
        if hasattr(obj, 'hotspot_count'):
            return obj.hotspot_count
        return obj.hotspots.count()

    def get_active_hotspot_count(self, obj) -> int:
        if hasattr(obj, 'active_hotspot_count'):
            return obj.active_hotspot_count
        return obj.hotspots.filter(is_active=True).count()

    def get_active_session_count(self, obj) -> int:
        if hasattr(obj, 'active_session_count'):
            return obj.active_session_count
        return HotspotSession.objects.filter(hotspot__location=obj, status='ACTIVE').count()

    def get_network_health(self, obj) -> str:
        return self._get_health_summary(obj)['network_health']

    def get_last_network_update_at(self, obj) -> Any:
        return self._get_health_summary(obj)['last_network_update_at']

    def get_network_summary(self, obj) -> Dict[str, Any]:
        return self._get_health_summary(obj)


class LocationCreateUpdateSerializer(serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = Location
        fields = [
            'id',
            'name',
            'code',
            'region',
            'district',
            'address',
            'latitude',
            'longitude',
            'timezone',
            'status',
            'site_type',
            'operating_hours',
            'installation_date',
            'external_reference',
            'contact_person',
            'contact_phone',
            'notes',
            'is_active',
        ]
        read_only_fields = ['id']


    def validate_latitude(self, value):
        if value is not None and not (Decimal('-90.0') <= value <= Decimal('90.0')):
            raise serializers.ValidationError("Latitude must be between -90.0 and +90.0 degrees.")
        return value

    def validate_longitude(self, value):
        if value is not None and not (Decimal('-180.0') <= value <= Decimal('180.0')):
            raise serializers.ValidationError("Longitude must be between -180.0 and +180.0 degrees.")
        return value

    def validate_timezone(self, value):
        if value and value not in zoneinfo.available_timezones():
            raise serializers.ValidationError(f"'{value}' is not a valid IANA timezone name.")
        return value

    def validate(self, attrs):
        company = self.context.get('company')
        code = attrs.get('code')
        if code and company:
            clean_code = code.strip().upper()
            attrs['code'] = clean_code
            existing = Location.objects.filter(company=company, code=clean_code)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError({"code": f"Location code '{clean_code}' is already in use for this company."})
        return attrs

    def create(self, validated_data):
        company = self.context.get('company')
        validated_data['company'] = company
        if not validated_data.get('code'):
            validated_data['code'] = generate_location_code(company, validated_data.get('name', ''))
        return super().create(validated_data)


class LocationRouterSummarySerializer(serializers.ModelSerializer):
    has_credentials = serializers.BooleanField(read_only=True)
    hotspots_count = serializers.SerializerMethodField()

    class Meta:
        model = Router
        fields = [
            'id',
            'name',
            'identity',
            'vendor',
            'model',
            'management_ip',
            'api_port',
            'use_tls',
            'health_status',
            'health_message',
            'has_credentials',
            'is_active',
            'last_seen_at',
            'last_health_check_at',
            'hotspots_count',
            'created_at',
        ]

    def get_hotspots_count(self, obj) -> int:
        return obj.hotspots.count() if hasattr(obj, 'hotspots') else 0


class LocationHotspotSummarySerializer(serializers.ModelSerializer):
    router_id = serializers.UUIDField(source='router.id', read_only=True, default=None)
    router_name = serializers.CharField(source='router.name', read_only=True, default=None)
    plans_count = serializers.SerializerMethodField()
    active_sessions_count = serializers.SerializerMethodField()

    class Meta:
        model = HotspotConfiguration
        fields = [
            'id',
            'name',
            'slug',
            'ssid',
            'interface_name',
            'is_default',
            'is_active',
            'router_id',
            'router_name',
            'plans_count',
            'active_sessions_count',
            'created_at',
        ]

    def get_plans_count(self, obj) -> int:
        return obj.plans.count() if hasattr(obj, 'plans') else 0

    def get_active_sessions_count(self, obj) -> int:
        return obj.sessions.filter(status='ACTIVE').count() if hasattr(obj, 'sessions') else 0


class LocationSessionSummarySerializer(serializers.ModelSerializer):
    hotspot_id = serializers.UUIDField(source='hotspot.id', read_only=True, default=None)
    hotspot_name = serializers.CharField(source='hotspot.name', read_only=True, default=None)
    session_id = serializers.CharField(source='acct_session_id', read_only=True)
    client_mac = serializers.CharField(source='mac_address', read_only=True)
    client_ip = serializers.CharField(source='ip_address', read_only=True)
    device_name = serializers.CharField(read_only=True)
    stop_time = serializers.DateTimeField(source='ended_at', read_only=True)
    bytes_in = serializers.IntegerField(source='input_bytes', read_only=True)
    bytes_out = serializers.IntegerField(source='output_bytes', read_only=True)
    duration_seconds = serializers.IntegerField(source='session_seconds', read_only=True)

    class Meta:
        model = HotspotSession
        fields = [
            'id',
            'session_id',
            'username',
            'client_mac',
            'client_ip',
            'device_name',
            'hotspot_id',
            'hotspot_name',
            'status',
            'started_at',
            'last_accounting_at',
            'stop_time',
            'bytes_in',
            'bytes_out',
            'total_bytes',
            'duration_seconds',
        ]



class MoveRouterSerializer(serializers.Serializer):
    router_id = serializers.UUIDField(required=True)
