from rest_framework import serializers

from ..models import Company, CompanyMembership


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            'id', 'name', 'slug', 'legal_name', 'phone', 'email',
            'country', 'currency', 'timezone', 'status', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class CompanyMembershipSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = CompanyMembership
        fields = ('id', 'company', 'company_name', 'user', 'user_email', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')
