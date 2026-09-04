from rest_framework import serializers

from ..models import RadiusClient


class RadiusAuthorizeSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=False, allow_blank=True, default='')
    nas_ip = serializers.IPAddressField(required=False, allow_null=True, default=None)
    nas_identifier = serializers.CharField(required=False, allow_blank=True, default='')
    mac_address = serializers.CharField(required=False, allow_blank=True, default='')

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)
        if data_copy.get('nas_ip') == '':
            data_copy['nas_ip'] = None
        return super().to_internal_value(data_copy)


class RadiusAccountingSerializer(serializers.Serializer):
    session_id = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    nas_ip = serializers.IPAddressField(required=True)
    nas_identifier = serializers.CharField(required=False, allow_blank=True, default='')
    packet_type = serializers.ChoiceField(choices=['Start', 'Interim-Update', 'Stop'], required=True)
    mac_address = serializers.CharField(required=False, allow_blank=True, default='')
    framed_ip = serializers.IPAddressField(required=False, allow_null=True, default=None)
    input_bytes = serializers.IntegerField(required=False, default=0)
    output_bytes = serializers.IntegerField(required=False, default=0)
    input_gigawords = serializers.IntegerField(required=False, default=0)
    output_gigawords = serializers.IntegerField(required=False, default=0)
    session_time = serializers.IntegerField(required=False, default=0)
    terminate_cause = serializers.CharField(required=False, allow_blank=True, default='')

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)
        for int_field in ['input_bytes', 'output_bytes', 'input_gigawords', 'output_gigawords', 'session_time']:
            val = data_copy.get(int_field)
            if val == '' or val is None:
                data_copy[int_field] = 0
            elif isinstance(val, str) and val.isdigit():
                data_copy[int_field] = int(val)
        if data_copy.get('framed_ip') == '':
            data_copy['framed_ip'] = None
        return super().to_internal_value(data_copy)


class RadiusClientSerializer(serializers.ModelSerializer):
    shared_secret = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = RadiusClient
        fields = [
            'id',
            'name',
            'nas_ip',
            'nas_identifier',
            'shared_secret',
            'is_active',
            'created_at',
            'updated_at',
        ]

    def create(self, validated_data):
        raw_secret = validated_data.pop('shared_secret', '')
        client = RadiusClient(**validated_data)
        if raw_secret:
            client.shared_secret = raw_secret
        client.save()
        return client
