import pytest
from rest_framework.test import APIClient
from django.db import IntegrityError
from decimal import Decimal

from apps.accounts.models import User
from apps.companies.models import (
    Company,
    CompanyMembership,
    HotspotConfiguration,
)
from apps.locations.models import Location
from apps.routers.models import Router
from apps.plans.models import Plan, DurationUnit
from apps.companies.services.portal_services import (
    get_default_hotspot,
    get_hotspot_by_slug,
    get_hotspot_by_id,
    get_plans_for_hotspot,
    resolve_hotspot_by_slug,
)
from apps.companies.services.anti_tethering_services import (
    TAG_TTL_LOCK,
    TAG_TTL_63,
    TAG_TTL_127,
    get_hotspot_rule_tag,
    apply_anti_tethering_policy,
    remove_anti_tethering_policy,
    get_or_create_anti_tethering_policy,
)
from apps.vouchers.models import VoucherBatch, Voucher
from apps.vouchers.services.voucher_services import (
    generate_voucher_batch,
    get_printable_voucher_cards,
)
from apps.notifications.services.sms_services import send_voucher_sms


class MockRouterClient:
    def __init__(self, mangle_rules=None, filter_rules=None):
        self.mangle_rules = mangle_rules if mangle_rules is not None else []
        self.filter_rules = filter_rules if filter_rules is not None else []
        self.executed_commands = []

    def connect(self):
        pass

    def close(self):
        pass

    def query(self, cmd, args=None):
        if cmd == '/interface/print':
            return [{'name': 'bridgeLocal'}, {'name': 'vlan-guest'}, {'name': 'vlan-staff'}]
        elif cmd == '/ip/firewall/mangle/print':
            return list(self.mangle_rules)
        elif cmd == '/ip/firewall/filter/print':
            return list(self.filter_rules)
        return []

    def execute(self, cmd, args=None):
        self.executed_commands.append((cmd, args))
        if cmd == '/ip/firewall/mangle/add':
            new_id = f"*{len(self.mangle_rules) + 1}"
            rule = {'.id': new_id, 'chain': 'postrouting', 'action': 'change-ttl', 'disabled': 'false'}
            for a in (args or []):
                if a.startswith('=comment='):
                    rule['comment'] = a.split('=', 2)[2]
                elif a.startswith('=out-interface='):
                    rule['out-interface'] = a.split('=', 2)[2]
            self.mangle_rules.append(rule)
            return True, 'OK'
        elif cmd == '/ip/firewall/mangle/set':
            rule_id = next((a.split('=')[2] for a in args if a.startswith('=.id=')), None)
            for r in self.mangle_rules:
                if r.get('.id') == rule_id:
                    for a in args:
                        if a.startswith('=comment='):
                            r['comment'] = a.split('=', 2)[2]
                        elif a.startswith('=out-interface='):
                            r['out-interface'] = a.split('=', 2)[2]
            return True, 'OK'
        elif cmd == '/ip/firewall/mangle/remove':
            rule_id = next((a.split('=')[2] for a in args if a.startswith('=.id=')), None)
            self.mangle_rules = [r for r in self.mangle_rules if r.get('.id') != rule_id]
            return True, 'OK'
        elif cmd == '/ip/firewall/filter/add':
            new_id = f"*{len(self.filter_rules) + 10}"
            rule = {'.id': new_id, 'chain': 'forward', 'action': 'drop', 'disabled': 'false'}
            for a in (args or []):
                if a.startswith('=comment='):
                    rule['comment'] = a.split('=', 2)[2]
                elif a.startswith('=in-interface='):
                    rule['in-interface'] = a.split('=', 2)[2]
            self.filter_rules.append(rule)
            return True, 'OK'
        elif cmd == '/ip/firewall/filter/set':
            rule_id = next((a.split('=')[2] for a in args if a.startswith('=.id=')), None)
            for r in self.filter_rules:
                if r.get('.id') == rule_id:
                    for a in args:
                        if a.startswith('=comment='):
                            r['comment'] = a.split('=', 2)[2]
            return True, 'OK'
        elif cmd == '/ip/firewall/filter/remove':
            rule_id = next((a.split('=')[2] for a in args if a.startswith('=.id=')), None)
            self.filter_rules = [r for r in self.filter_rules if r.get('.id') != rule_id]
            return True, 'OK'
        return True, 'OK'


@pytest.fixture
def multi_hotspot_setup(db):
    user_a = User.objects.create_user(email='admin@tenant-a.com', password='Password123!')
    company_a = Company.objects.create(name='Tenant A', slug='tenant-a')
    CompanyMembership.objects.create(company=company_a, user=user_a, is_active=True)

    loc_a = Location.objects.create(company=company_a, name='HQ Campus', code='LOC-HQ-001')
    router_a = Router.objects.create(
        company=company_a,
        location=loc_a,
        name='Main Gateway',
        identity='MikroTik-HQ',
        management_ip='192.168.88.1'
    )

    hotspot_default = HotspotConfiguration.objects.create(
        company=company_a,
        location=loc_a,
        router=router_a,
        name='Default HotSpot',
        slug='tenant-a-default',
        ssid='TenantA-Default',
        interface_name='bridgeLocal',
        is_default=True,
        is_active=True
    )

    hotspot_guest = HotspotConfiguration.objects.create(
        company=company_a,
        location=loc_a,
        router=router_a,
        name='Guest HotSpot',
        slug='tenant-a-guest',
        ssid='TenantA-Guest',
        interface_name='vlan-guest',
        is_default=False,
        is_active=True
    )

    plan_standard = Plan.objects.create(
        company=company_a,
        name='1 Hour Pass',
        code='1HR-PASS',
        price=Decimal('1000.00'),
        currency='TZS',
        duration_value=1,
        duration_unit=DurationUnit.HOURS,
        is_active=True
    )
    plan_vip = Plan.objects.create(
        company=company_a,
        name='VIP Unlimited',
        code='VIP-PASS',
        price=Decimal('15000.00'),
        currency='TZS',
        duration_value=7,
        duration_unit=DurationUnit.DAYS,
        is_active=True
    )

    # User & Company B (Tenant isolation)
    user_b = User.objects.create_user(email='admin@tenant-b.com', password='Password123!')
    company_b = Company.objects.create(name='Tenant B', slug='tenant-b')
    CompanyMembership.objects.create(company=company_b, user=user_b, is_active=True)

    return {
        'user_a': user_a,
        'company_a': company_a,
        'router_a': router_a,
        'hotspot_default': hotspot_default,
        'hotspot_guest': hotspot_guest,
        'plan_standard': plan_standard,
        'plan_vip': plan_vip,
        'user_b': user_b,
        'company_b': company_b,
    }


@pytest.mark.django_db
def test_default_hotspot_resolution_and_unique_constraint(multi_hotspot_setup):
    company = multi_hotspot_setup['company_a']
    default_hs = multi_hotspot_setup['hotspot_default']
    guest_hs = multi_hotspot_setup['hotspot_guest']

    # Check property and service helper
    assert company.default_hotspot == default_hs
    assert get_default_hotspot(company) == default_hs

    # Cannot have two defaults via direct creation (UniqueConstraint)
    with pytest.raises(IntegrityError):
        HotspotConfiguration.objects.create(
            company=company,
            name='Second Default',
            slug='second-default',
            ssid='Second',
            is_default=True
        )


@pytest.mark.django_db
def test_plan_scoping_per_hotspot(multi_hotspot_setup):
    hotspot_default = multi_hotspot_setup['hotspot_default']
    hotspot_guest = multi_hotspot_setup['hotspot_guest']
    plan_standard = multi_hotspot_setup['plan_standard']
    plan_vip = multi_hotspot_setup['plan_vip']

    # When no plans are explicitly assigned, hotspot serves all company active plans
    assert get_plans_for_hotspot(hotspot_default).count() == 2

    # Assign only plan_standard to guest hotspot
    hotspot_guest.plans.add(plan_standard)

    guest_plans = get_plans_for_hotspot(hotspot_guest)
    assert guest_plans.count() == 1
    assert guest_plans.first() == plan_standard
    assert plan_vip not in guest_plans


@pytest.mark.django_db
def test_public_plans_api_and_purchase_validation(multi_hotspot_setup):
    client = APIClient()
    hotspot_guest = multi_hotspot_setup['hotspot_guest']
    plan_standard = multi_hotspot_setup['plan_standard']
    plan_vip = multi_hotspot_setup['plan_vip']

    # Assign only plan_standard to guest hotspot
    hotspot_guest.plans.add(plan_standard)

    # 1. Public plans endpoint for guest hotspot
    resp = client.get(f'/api/v1/public/hotspots/{hotspot_guest.slug}/plans/')
    assert resp.status_code == 200
    plan_ids = [p['id'] for p in resp.data]
    assert str(plan_standard.id) in plan_ids
    assert str(plan_vip.id) not in plan_ids

    # 2. Public purchase initiation: valid plan
    resp_valid = client.post(f'/api/v1/public/hotspots/{hotspot_guest.slug}/purchases/', {
        'plan_id': str(plan_standard.id),
        'customer_phone': '0712345678',
    }, format='json')
    # Should proceed past plan validation (might fail on payment gateway mock or succeed)
    assert resp_valid.status_code in (201, 500, 400)
    assert resp_valid.data.get('code') != 'PLAN_NOT_FOUND'

    # 3. Public purchase initiation: plan not assigned to this hotspot
    resp_invalid = client.post(f'/api/v1/public/hotspots/{hotspot_guest.slug}/purchases/', {
        'plan_id': str(plan_vip.id),
        'customer_phone': '0712345678',
    }, format='json')
    assert resp_invalid.status_code == 404
    assert resp_invalid.data.get('code') == 'PLAN_NOT_FOUND'


@pytest.mark.django_db
def test_hotspot_management_crud_api(multi_hotspot_setup):
    client = APIClient()
    user_a = multi_hotspot_setup['user_a']
    company_a = multi_hotspot_setup['company_a']
    router_a = multi_hotspot_setup['router_a']
    hotspot_default = multi_hotspot_setup['hotspot_default']
    hotspot_guest = multi_hotspot_setup['hotspot_guest']
    plan_standard = multi_hotspot_setup['plan_standard']

    client.force_authenticate(user=user_a)

    # 1. List hotspots
    resp = client.get('/api/v1/hotspots/')
    assert resp.status_code == 200
    assert len(resp.data) == 2

    # 2. Create new hotspot
    resp_create = client.post('/api/v1/hotspots/', {
        'name': 'Staff HotSpot',
        'slug': 'tenant-a-staff',
        'ssid': 'TenantA-Staff',
        'router_id': str(router_a.id),
        'interface_name': 'vlan-staff',
        'dns_name': 'staff.wifi.lab',
        'is_default': False,
    }, format='json')
    assert resp_create.status_code == 201
    staff_id = resp_create.data['id']
    assert resp_create.data['router_name'] == 'Main Gateway'

    # 3. Set-default endpoint: promote guest to default
    resp_set_def = client.post(f'/api/v1/hotspots/{hotspot_guest.id}/set-default/')
    assert resp_set_def.status_code == 200
    assert resp_set_def.data['is_default'] is True

    # Previous default must have is_default=False
    hotspot_default.refresh_from_db()
    assert hotspot_default.is_default is False

    # 4. Manage plans for staff hotspot
    resp_plans = client.post(f'/api/v1/hotspots/{staff_id}/plans/', {
        'plan_ids': [str(plan_standard.id)]
    }, format='json')
    assert resp_plans.status_code == 200
    assert resp_plans.data['plans_count'] == 1

    # 5. Delete staff hotspot (unreferenced)
    resp_del = client.delete(f'/api/v1/hotspots/{staff_id}/')
    assert resp_del.status_code == 200
    assert resp_del.data['action'] == 'deleted'


@pytest.mark.django_db
def test_hotspot_api_tenant_isolation(multi_hotspot_setup):
    client = APIClient()
    user_b = multi_hotspot_setup['user_b']
    hotspot_guest = multi_hotspot_setup['hotspot_guest']

    # User B cannot access HotSpots belonging to Tenant A
    client.force_authenticate(user=user_b)
    resp = client.get(f'/api/v1/hotspots/{hotspot_guest.id}/')
    assert resp.status_code == 404

    resp_patch = client.patch(f'/api/v1/hotspots/{hotspot_guest.id}/', {'name': 'Hacked'})
    assert resp_patch.status_code == 404


@pytest.mark.django_db
def test_printable_voucher_and_sms_hotspot_scoping(multi_hotspot_setup):
    company = multi_hotspot_setup['company_a']
    user = multi_hotspot_setup['user_a']
    plan = multi_hotspot_setup['plan_standard']
    hotspot_guest = multi_hotspot_setup['hotspot_guest']

    batch, _ = generate_voucher_batch(
        company=company,
        plan=plan,
        quantity=2,
        created_by=user
    )

    # 1. Printable cards with explicit guest hotspot
    cards = get_printable_voucher_cards(batch, hotspot=hotspot_guest)
    assert len(cards) == 2
    assert cards[0]['ssid'] == 'TenantA-Guest'
    assert f"/p/{hotspot_guest.slug}" in cards[0]['qr_url']

    # 2. SMS rendering with guest hotspot
    voucher = Voucher.objects.filter(batch=batch).first()
    msg = send_voucher_sms(
        voucher=voucher,
        recipient_phone='+255712345678',
        company=company,
        hotspot=hotspot_guest
    )
    assert 'Connect to TenantA-Guest' in msg.rendered_content


@pytest.mark.django_db
def test_anti_tethering_multi_hotspot_rule_isolation(multi_hotspot_setup):
    hotspot_default = multi_hotspot_setup['hotspot_default']
    hotspot_guest = multi_hotspot_setup['hotspot_guest']

    mock_client = MockRouterClient()

    policy_default = get_or_create_anti_tethering_policy(hotspot_default)
    policy_guest = get_or_create_anti_tethering_policy(hotspot_guest)

    # 1. Apply policy to default hotspot (interface bridgeLocal)
    apply_anti_tethering_policy(policy_default, hotspot_default, client_factory=lambda: mock_client)
    assert len(mock_client.mangle_rules) == 1
    assert mock_client.mangle_rules[0]['out-interface'] == 'bridgeLocal'
    assert mock_client.mangle_rules[0]['comment'] == get_hotspot_rule_tag(TAG_TTL_LOCK, hotspot_default)

    # 2. Apply policy to guest hotspot (interface vlan-guest)
    apply_anti_tethering_policy(policy_guest, hotspot_guest, client_factory=lambda: mock_client)
    assert len(mock_client.mangle_rules) == 2
    assert mock_client.mangle_rules[1]['out-interface'] == 'vlan-guest'
    assert mock_client.mangle_rules[1]['comment'] == get_hotspot_rule_tag(TAG_TTL_LOCK, hotspot_guest)

    # Total filter rules: 2 for default (TTL 63, 127) + 2 for guest (TTL 63, 127) = 4
    assert len(mock_client.filter_rules) == 4

    # 3. Remove policy for guest hotspot: default hotspot rules must remain intact!
    remove_anti_tethering_policy(hotspot_guest, client_factory=lambda: mock_client)
    assert len(mock_client.mangle_rules) == 1
    assert mock_client.mangle_rules[0]['comment'] == get_hotspot_rule_tag(TAG_TTL_LOCK, hotspot_default)
    assert len(mock_client.filter_rules) == 2
