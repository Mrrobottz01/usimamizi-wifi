from django.db import migrations


def backfill_default_hotspot(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    HotspotConfiguration = apps.get_model('companies', 'HotspotConfiguration')

    for company in Company.objects.all():
        hotspots = HotspotConfiguration.objects.filter(company=company).order_by('-is_active', 'created_at')
        if hotspots.exists():
            # Check if any is already marked default
            default_hs = hotspots.filter(is_default=True).first()
            if not default_hs:
                first_hs = hotspots.first()
                first_hs.is_default = True
                first_hs.save(update_fields=['is_default'])


def reverse_default_hotspot(apps, schema_editor):
    HotspotConfiguration = apps.get_model('companies', 'HotspotConfiguration')
    HotspotConfiguration.objects.all().update(is_default=False)


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0010_hotspotconfiguration_is_default_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_default_hotspot, reverse_default_hotspot),
    ]
