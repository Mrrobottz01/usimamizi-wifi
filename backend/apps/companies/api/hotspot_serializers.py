from rest_framework import serializers

from apps.companies.models import HotspotConfiguration
from apps.plans.models import Plan


class HotspotPlanSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id',
            'name',
            'price',
            'currency',
            'duration_value',
            'duration_unit',
            'download_speed_kbps',
            'upload_speed_kbps',
            'is_active',
        ]


class HotspotListSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    router_name = serializers.CharField(source='router.name', read_only=True)
    plans_count = serializers.SerializerMethodField()
    active_sessions_count = serializers.SerializerMethodField()

    class Meta:
        model = HotspotConfiguration
        fields = [
            'id',
            'company',
            'location',
            'location_name',
            'router',
            'router_name',
            'name',
            'slug',
            'ssid',
            'interface_name',
            'server_name',
            'gateway_ip',
            'subnet_mask',
            'router_login_url',
            'is_active',
            'is_default',
            'plans_count',
            'active_sessions_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'company',
            'location_name',
            'router_name',
            'plans_count',
            'active_sessions_count',
            'created_at',
            'updated_at',
        ]

    def get_plans_count(self, obj) -> int:
        return obj.plans.count()

    def get_active_sessions_count(self, obj) -> int:
        return obj.sessions.filter(status='ACTIVE').count() if hasattr(obj, 'sessions') else 0


class HotspotDetailSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True, default=None)
    router_name = serializers.CharField(source='router.name', read_only=True, default=None)
    plans = HotspotPlanSummarySerializer(many=True, read_only=True)
    active_sessions_count = serializers.SerializerMethodField()

    class Meta:
        model = HotspotConfiguration
        fields = [
            'id',
            'company',
            'location',
            'location_name',
            'router',
            'router_name',
            'name',
            'slug',
            'ssid',
            'interface_name',
            'server_name',
            'gateway_ip',
            'subnet_mask',
            'router_login_url',
            'is_active',
            'is_default',
            'brand_name',
            'headline',
            'welcome_text',
            'primary_color',
            'logo_url',
            'support_phone',
            'terms_url',
            'privacy_url',
            'default_language',
            'plans',
            'active_sessions_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'company',
            'location_name',
            'router_name',
            'plans',
            'active_sessions_count',
            'created_at',
            'updated_at',
        ]

    def get_active_sessions_count(self, obj) -> int:
        return obj.sessions.filter(status='ACTIVE').count() if hasattr(obj, 'sessions') else 0


class HotspotCreateUpdateSerializer(serializers.ModelSerializer):
    plan_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        help_text="List of plan UUIDs to assign to this hotspot"
    )

    class Meta:
        model = HotspotConfiguration
        fields = [
            'id',
            'location',
            'router',
            'name',
            'slug',
            'ssid',
            'interface_name',
            'server_name',
            'gateway_ip',
            'subnet_mask',
            'router_login_url',
            'is_active',
            'is_default',
            'brand_name',
            'headline',
            'welcome_text',
            'primary_color',
            'logo_url',
            'support_phone',
            'terms_url',
            'privacy_url',
            'default_language',
            'plan_ids',
        ]

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        if 'router_id' in data and 'router' not in data:
            data['router'] = data.pop('router_id')
        if 'location_id' in data and 'location' not in data:
            data['location'] = data.pop('location_id')
        return super().to_internal_value(data)

    def validate(self, attrs):
        company = self.context.get('company')
        location = attrs.get('location') or getattr(self.instance, 'location', None)
        router = attrs.get('router') or getattr(self.instance, 'router', None)

        if location and company and location.company_id != company.id:
            raise serializers.ValidationError({"location": "Location must belong to the same company."})
        if router and company and router.company_id != company.id:
            raise serializers.ValidationError({"router": "Router must belong to the same company."})
        if location and router and router.location_id and router.location_id != location.id:
            raise serializers.ValidationError({"location": "Hotspot location must match the hosting router location."})

        # Slug validation
        slug = attrs.get('slug')
        if slug:
            clean_slug = slug.strip().lower()
            attrs['slug'] = clean_slug
            existing = HotspotConfiguration.objects.filter(slug__iexact=clean_slug)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError({"slug": f"Slug '{clean_slug}' is already taken."})

        return attrs

    def create(self, validated_data):
        plan_ids = validated_data.pop('plan_ids', None)
        company = self.context.get('company')
        is_default = validated_data.get('is_default', False)

        if is_default:
            HotspotConfiguration.objects.filter(company=company, is_default=True).update(is_default=False)

        hotspot = HotspotConfiguration.objects.create(company=company, **validated_data)

        if plan_ids is not None:
            plans = Plan.objects.filter(company=company, id__in=plan_ids)
            hotspot.plans.set(plans)

        return hotspot

    def update(self, instance, validated_data):
        plan_ids = validated_data.pop('plan_ids', None)
        is_default = validated_data.get('is_default')

        if is_default and not instance.is_default:
            HotspotConfiguration.objects.filter(company=instance.company, is_default=True).exclude(id=instance.id).update(is_default=False)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if plan_ids is not None:
            plans = Plan.objects.filter(company=instance.company, id__in=plan_ids)
            instance.plans.set(plans)

        return instance
