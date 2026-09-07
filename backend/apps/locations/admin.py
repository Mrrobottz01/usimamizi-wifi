from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'company', 'region', 'status', 'is_active', 'created_at')
    list_filter = ('company', 'status', 'is_active', 'region')
    search_fields = ('name', 'code', 'region', 'district', 'contact_person')
    readonly_fields = ('created_at', 'updated_at')
