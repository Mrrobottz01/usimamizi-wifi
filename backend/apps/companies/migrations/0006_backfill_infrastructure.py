from django.db import migrations


def backfill_infrastructure(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    Location = apps.get_model('locations', 'Location')
    Router = apps.get_model('routers', 'Router')
    RadiusClient = apps.get_model('radius', 'RadiusClient')
    HotspotConfiguration = apps.get_model('companies', 'HotspotConfiguration')
    RouterUplinkProfile = apps.get_model('companies', 'RouterUplinkProfile')

    for company in Company.objects.all():
        # 1. Seed exactly one default Location per existing Company
        default_location = Location.objects.filter(company=company).first()
        if not default_location:
            default_location = Location.objects.create(
                company=company,
                name=f"{company.name} Main Site",
                code="LOC-MAIN-001",
                region="",
                district="",
                address="",
                status="ACTIVE",
                is_active=True
            )

        # 2. For each existing RadiusClient, create or link a Router
        company_routers = []
        for rc in RadiusClient.objects.filter(company=company):
            if rc.router_id:
                router = Router.objects.get(id=rc.router_id)
            else:
                router = Router.objects.create(
                    company=company,
                    location=default_location,
                    name=rc.name,
                    identity=rc.nas_identifier or rc.name,
                    vendor="MikroTik",
                    model="",
                    serial_number="",
                    management_ip=rc.nas_ip,  # Explicit fallback migration mapping
                    api_port=8728,
                    use_tls=False,
                    api_username="admin",
                    api_password_encrypted="",
                    routeros_version="",
                    health_status="UNKNOWN",
                    is_active=rc.is_active
                )
                rc.router = router
                rc.save(update_fields=['router'])
            company_routers.append(router)

        # Determine primary router for company (prefer gateway 10.5.50.1, fallback to first)
        primary_router = None
        for r in company_routers:
            if r.management_ip == '10.5.50.1':
                primary_router = r
                break
        if not primary_router and company_routers:
            primary_router = company_routers[0]

        # 3. Backfill HotspotConfiguration
        for hotspot in HotspotConfiguration.objects.filter(company=company):
            update_fields = []
            if not hotspot.location_id:
                hotspot.location = default_location
                update_fields.append('location')
            if not hotspot.router_id and primary_router:
                hotspot.router = primary_router
                update_fields.append('router')
            if not hotspot.gateway_ip:
                hotspot.gateway_ip = "10.5.50.1"
                update_fields.append('gateway_ip')
            if update_fields:
                hotspot.save(update_fields=update_fields)

        # 4. Backfill RouterUplinkProfile
        for uplink in RouterUplinkProfile.objects.filter(company=company):
            if not uplink.router_id and primary_router:
                uplink.router = primary_router
                uplink.save(update_fields=['router'])


def reverse_backfill(apps, schema_editor):
    """
    Reverse migration: clear backfilled links without destroying companies or core records.
    """
    RadiusClient = apps.get_model('radius', 'RadiusClient')
    HotspotConfiguration = apps.get_model('companies', 'HotspotConfiguration')
    RouterUplinkProfile = apps.get_model('companies', 'RouterUplinkProfile')
    Router = apps.get_model('routers', 'Router')
    Location = apps.get_model('locations', 'Location')

    RadiusClient.objects.all().update(router=None)
    HotspotConfiguration.objects.all().update(location=None, router=None)
    RouterUplinkProfile.objects.all().update(router=None)
    Router.objects.all().delete()
    Location.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0005_hotspot_location_router_network_fields'),
        ('radius', '0003_radiusclient_router'),
        ('locations', '0001_initial'),
        ('routers', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_infrastructure, reverse_backfill),
    ]
