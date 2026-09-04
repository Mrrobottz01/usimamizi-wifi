import pytest

from apps.companies.models import Company, HotspotConfiguration
from apps.payments.models import (
    HotspotWalledGardenEntry,
    WalledGardenEntryType,
    WalledGardenPurpose,
)
from apps.payments.services.walled_garden_services import (
    apply_walled_garden_preset,
    generate_routeros_walled_garden_script,
)


@pytest.fixture
def walled_garden_setup(db):
    company = Company.objects.create(name='Walled Garden Co', slug='wg-co')
    hotspot = HotspotConfiguration.objects.create(
        company=company,
        name='WG HotSpot',
        slug='wg-hotspot'
    )
    return {'company': company, 'hotspot': hotspot}


@pytest.mark.django_db
def test_apply_snippe_payments_preset(walled_garden_setup):
    company = walled_garden_setup['company']
    hotspot = walled_garden_setup['hotspot']

    entries = apply_walled_garden_preset(
        company=company,
        hotspot=hotspot,
        preset_name='Snippe Payments'
    )

    assert len(entries) == 3
    hosts = [e.host for e in entries]
    assert 'api.snippe.sh' in hosts
    assert 'snippe.sh' in hosts
    assert 'snippe.me' in hosts

    # Idempotent re-application
    apply_walled_garden_preset(
        company=company,
        hotspot=hotspot,
        preset_name='Snippe Payments'
    )
    assert HotspotWalledGardenEntry.objects.filter(company=company).count() == 3


@pytest.mark.django_db
def test_generate_routeros_walled_garden_script(walled_garden_setup):
    company = walled_garden_setup['company']
    hotspot = walled_garden_setup['hotspot']

    HotspotWalledGardenEntry.objects.create(
        company=company,
        hotspot=hotspot,
        entry_type=WalledGardenEntryType.DOMAIN,
        host='api.snippe.sh',
        purpose=WalledGardenPurpose.PAYMENT,
        description='Snippe API'
    )
    HotspotWalledGardenEntry.objects.create(
        company=company,
        hotspot=hotspot,
        entry_type=WalledGardenEntryType.IP,
        address='10.5.50.254',
        purpose=WalledGardenPurpose.PORTAL,
        description='Portal Server'
    )

    script = generate_routeros_walled_garden_script(company=company)

    assert '/ip hotspot walled-garden add dst-host="api.snippe.sh"' in script
    assert '/ip hotspot walled-garden ip add dst-address="10.5.50.254" action=accept' in script
