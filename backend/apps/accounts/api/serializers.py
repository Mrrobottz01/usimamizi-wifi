from rest_framework import serializers

from ..models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'phone', 'first_name', 'last_name', 'full_name', 'is_active', 'is_staff', 'created_at')
        read_only_fields = ('id', 'is_active', 'is_staff', 'created_at')


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
