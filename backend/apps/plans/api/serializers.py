from rest_framework import serializers

from ..models import DurationUnit, Plan, ValidityMode


class PlanSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(source='company.id', read_only=True)
    duration_unit_display = serializers.CharField(source='get_duration_unit_display', read_only=True)
    validity_mode_display = serializers.CharField(source='get_validity_mode_display', read_only=True)

    class Meta:
        model = Plan
        fields = [
            'id',
            'company_id',
            'name',
            'code',
            'description',
            'price',
            'currency',
            'duration_value',
            'duration_unit',
            'duration_unit_display',
            'validity_mode',
            'validity_mode_display',
            'download_speed_kbps',
            'upload_speed_kbps',
            'data_limit_bytes',
            'max_devices',
            'simultaneous_sessions',
            'idle_timeout_seconds',
            'session_timeout_seconds',
            'is_active',
            'sort_order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlanCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    code = serializers.CharField(max_length=64, required=True)
    description = serializers.CharField(allow_blank=True, default='')
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    currency = serializers.CharField(max_length=3, default='TZS')

    duration_value = serializers.IntegerField(default=1, min_value=1)
    duration_unit = serializers.ChoiceField(choices=DurationUnit.choices, default=DurationUnit.HOURS)
    validity_mode = serializers.ChoiceField(choices=ValidityMode.choices, default=ValidityMode.CONTINUOUS)

    download_speed_kbps = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    upload_speed_kbps = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    data_limit_bytes = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    max_devices = serializers.IntegerField(default=1, min_value=1)
    simultaneous_sessions = serializers.IntegerField(default=1, min_value=1)

    idle_timeout_seconds = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    session_timeout_seconds = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    is_active = serializers.BooleanField(default=True)
    sort_order = serializers.IntegerField(default=0)
