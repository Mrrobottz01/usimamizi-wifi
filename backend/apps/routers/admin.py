from django.contrib import admin
from .models import Router


@admin.register(Router)
class RouterAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'identity',
        'company',
        'location',
        'management_ip',
        'model',
        'health_status',
        'routeros_version',
        'is_active',
        'last_seen_at'
    )
    list_filter = ('company', 'location', 'health_status', 'is_active', 'vendor')
    search_fields = ('name', 'identity', 'management_ip', 'serial_number', 'model')
    readonly_fields = ('created_at', 'updated_at', 'last_seen_at', 'system_resources')
    exclude = ('api_password_encrypted',)
