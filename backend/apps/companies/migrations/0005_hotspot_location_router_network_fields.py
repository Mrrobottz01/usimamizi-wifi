import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0004_antitetheringpolicy'),
        ('locations', '0001_initial'),
        ('routers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='hotspotconfiguration',
            name='gateway_ip',
            field=models.GenericIPAddressField(blank=True, help_text='Customer default gateway IP on hotspot network (e.g. 10.5.50.1)', null=True),
        ),
        migrations.AddField(
            model_name='hotspotconfiguration',
            name='interface_name',
            field=models.CharField(blank=True, default='bridgeLocal', help_text='Router interface or bridge e.g. bridgeLocal, vlan10', max_length=64),
        ),
        migrations.AddField(
            model_name='hotspotconfiguration',
            name='location',
            field=models.ForeignKey(blank=True, help_text='Physical venue/location of this hotspot', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hotspots', to='locations.location'),
        ),
        migrations.AddField(
            model_name='hotspotconfiguration',
            name='router',
            field=models.ForeignKey(blank=True, help_text='Router hosting this hotspot service', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hotspots', to='routers.router'),
        ),
        migrations.AddField(
            model_name='hotspotconfiguration',
            name='server_name',
            field=models.CharField(blank=True, default='hotspot1', help_text='MikroTik /ip hotspot server name', max_length=64),
        ),
        migrations.AddField(
            model_name='hotspotconfiguration',
            name='subnet_mask',
            field=models.CharField(blank=True, default='255.255.255.0', help_text='Subnet mask or CIDR e.g. 255.255.255.0 or /24', max_length=32),
        ),
        migrations.AddField(
            model_name='routeruplinkprofile',
            name='router',
            field=models.ForeignKey(blank=True, help_text='Optional router this uplink profile belongs to', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uplink_profiles', to='routers.router'),
        ),
        migrations.AddIndex(
            model_name='hotspotconfiguration',
            index=models.Index(fields=['company', 'router'], name='hotspot_con_company_6035ab_idx'),
        ),
        migrations.AddIndex(
            model_name='hotspotconfiguration',
            index=models.Index(fields=['company', 'location'], name='hotspot_con_company_dbdd55_idx'),
        ),
        migrations.AddIndex(
            model_name='hotspotconfiguration',
            index=models.Index(fields=['company', 'slug'], name='hotspot_con_company_a94e90_idx'),
        ),
    ]
