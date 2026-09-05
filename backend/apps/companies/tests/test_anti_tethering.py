import pytest
from unittest.mock import MagicMock
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.companies.models import Company, CompanyMembership, HotspotConfiguration, AntiTetheringPolicy, IPv6Policy
from apps.companies.services.anti_tethering_services import (
    TAG_TTL_LOCK,
    TAG_TTL_63,
    TAG_TTL_127,
    get_or_create_anti_tethering_policy,
    get_anti_tethering_status,
    get_anti_tethering_counters,
    apply_anti_tethering_policy,
    remove_anti_tethering_policy,
    sync_anti_tethering_policy,
    restore_default_anti_tethering_policy,
)


@pytest.fixture
def anti_tether_setup(db):
    user_a = User.objects.create_user(email='admin@companya.com', password='Password123!')
    company_a = Company.objects.create(name='Company A', slug='company-a')
    CompanyMembership.objects.create(company=company_a, user=user_a, is_active=True)
    hotspot_a = HotspotConfiguration.objects.create(
        company=company_a,
        name='Main HotSpot A',
        slug='hotspot-a',
        ssid='CompanyA-WiFi'
    )

    user_b = User.objects.create_user(email='admin@companyb.com', password='Password123!')
    company_b = Company.objects.create(name='Company B', slug='company-b')
    CompanyMembership.objects.create(company=company_b, user=user_b, is_active=True)
    hotspot_b = HotspotConfiguration.objects.create(
        company=company_b,
        name='Main HotSpot B',
        slug='hotspot-b',
        ssid='CompanyB-WiFi'
    )

    return {
        'user_a': user_a,
        'company_a': company_a,
        'hotspot_a': hotspot_a,
        'user_b': user_b,
        'company_b': company_b,
        'hotspot_b': hotspot_b,
    }


class MockRouterOSClient:
    def __init__(self, reachable=True, mangle_rules=None, filter_rules=None):
        self.reachable = reachable
        self.mangle_rules = mangle_rules if mangle_rules is not None else []
        self.filter_rules = filter_rules if filter_rules is not None else []
        self.executed_commands = []

    def connect(self):
        if not self.reachable:
            raise RuntimeError("Connection timed out to RouterOS API")

    def close(self):
        pass

    def query(self, cmd, args=None):
        if cmd == '/interface/print':
            return [{'name': 'bridgeLocal'}]
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
                elif a.startswith('=new-ttl='):
                    rule['new-ttl'] = a.split('=', 2)[2]
            self.mangle_rules.append(rule)
            return True, 'OK'
        elif cmd == '/ip/firewall/mangle/set':
            rule_id = next((a.split('=')[2] for a in args if a.startswith('=.id=')), None)
            for r in self.mangle_rules:
                if r.get('.id') == rule_id:
                    for a in args:
                        if a.startswith('=comment='):
                            r['comment'] = a.split('=', 2)[2]
                        elif a.startswith('=new-ttl='):
                            r['new-ttl'] = a.split('=', 2)[2]
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
                elif a.startswith('=ttl='):
                    rule['ttl'] = a.split('=', 2)[2]
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


@pytest.mark.django_db
def test_policy_creation_defaults(anti_tether_setup):
    hotspot = anti_tether_setup['hotspot_a']
    policy = get_or_create_anti_tethering_policy(hotspot)

    assert policy is not None
    assert policy.enabled is True
    assert policy.max_devices == 1
    assert policy.simultaneous_sessions == 1
    assert policy.ttl_lock_enabled is True
    assert policy.ttl_lock_value == 1
    assert policy.detect_ttl_63 is True
    assert policy.detect_ttl_127 is True
    assert policy.strict_mode is False
    assert policy.ipv6_policy == IPv6Policy.DISABLED


@pytest.mark.django_db
def test_status_detection_active(anti_tether_setup):
    hotspot = anti_tether_setup['hotspot_a']
    mock_mangle = [{
        '.id': '*1',
        'comment': TAG_TTL_LOCK,
        'action': 'change-ttl',
        'new-ttl': 'set:1',
        'disabled': 'false',
        'packets': '120',
        'bytes': '15000'
    }]
    mock_filter = [
        {'.id': '*2', 'comment': TAG_TTL_63, 'action': 'drop', 'disabled': 'false', 'packets': '5', 'bytes': '320'},
        {'.id': '*3', 'comment': TAG_TTL_127, 'action': 'drop', 'disabled': 'false', 'packets': '2', 'bytes': '120'},
    ]

    mock_client = MockRouterOSClient(reachable=True, mangle_rules=mock_mangle, filter_rules=mock_filter)
    status = get_anti_tethering_status(hotspot, client_factory=lambda: mock_client)

    assert status['router_reachable'] is True
    assert status['ttl_lock_active'] is True
    assert status['ttl_63_active'] is True
    assert status['ttl_127_active'] is True
    assert status['status'] == 'ACTIVE'


@pytest.mark.django_db
def test_status_router_unreachable(anti_tether_setup):
    hotspot = anti_tether_setup['hotspot_a']
    mock_client = MockRouterOSClient(reachable=False)
    status = get_anti_tethering_status(hotspot, client_factory=lambda: mock_client)

    assert status['router_reachable'] is False
    assert status['status'] == 'ROUTER_UNREACHABLE'
    assert status['error'] is not None


@pytest.mark.django_db
def test_legacy_rule_adoption_and_idempotence(anti_tether_setup):
    hotspot = anti_tether_setup['hotspot_a']
    policy = get_or_create_anti_tethering_policy(hotspot)

    # Pre-populate router with legacy comment strings
    legacy_mangle = [{
        '.id': '*legacy1',
        'comment': 'Usimamizi: Anti-Tethering (Block Hotspot Sharing)',
        'action': 'change-ttl',
        'new-ttl': 'set:1',
        'disabled': 'false',
    }]
    legacy_filter = [
        {'.id': '*legacy2', 'comment': 'Usimamizi: Anti-Tethering Drop forwarded client packets (TTL 63)', 'action': 'drop', 'disabled': 'false'},
        {'.id': '*legacy3', 'comment': 'Usimamizi: Anti-Tethering Drop forwarded client packets (TTL 127)', 'action': 'drop', 'disabled': 'false'},
    ]

    mock_client = MockRouterOSClient(reachable=True, mangle_rules=legacy_mangle, filter_rules=legacy_filter)

    # First sync: should adopt legacy rules and rename comments
    success, msg, _ = apply_anti_tethering_policy(policy, hotspot, client_factory=lambda: mock_client)
    assert success is True
    assert len(mock_client.mangle_rules) == 1
    assert mock_client.mangle_rules[0]['comment'] == TAG_TTL_LOCK
    assert len(mock_client.filter_rules) == 2
    assert any(r['comment'] == TAG_TTL_63 for r in mock_client.filter_rules)
    assert any(r['comment'] == TAG_TTL_127 for r in mock_client.filter_rules)

    # Second sync: idempotent, must NOT duplicate rules
    success2, msg2, _ = apply_anti_tethering_policy(policy, hotspot, client_factory=lambda: mock_client)
    assert success2 is True
    assert len(mock_client.mangle_rules) == 1
    assert len(mock_client.filter_rules) == 2


@pytest.mark.django_db
def test_disable_policy_removes_managed_rules_only(anti_tether_setup):
    hotspot = anti_tether_setup['hotspot_a']
    policy = get_or_create_anti_tethering_policy(hotspot)
    policy.enabled = False
    policy.save()

    mock_mangle = [
        {'.id': '*1', 'comment': TAG_TTL_LOCK, 'action': 'change-ttl', 'disabled': 'false'},
        {'.id': '*99', 'comment': 'Unrelated Hotspot Mangle Rule', 'action': 'mark-packet', 'disabled': 'false'},
    ]
    mock_filter = [
        {'.id': '*2', 'comment': TAG_TTL_63, 'action': 'drop', 'disabled': 'false'},
        {'.id': '*100', 'comment': 'Customer Port 25 Drop', 'action': 'drop', 'disabled': 'false'},
    ]

    mock_client = MockRouterOSClient(reachable=True, mangle_rules=mock_mangle, filter_rules=mock_filter)
    apply_anti_tethering_policy(policy, hotspot, client_factory=lambda: mock_client)

    # Mangle rule *1 should be removed, *99 must remain intact
    assert len(mock_client.mangle_rules) == 1
    assert mock_client.mangle_rules[0]['.id'] == '*99'

    # Filter rule *2 should be removed, *100 must remain intact
    assert len(mock_client.filter_rules) == 1
    assert mock_client.filter_rules[0]['.id'] == '*100'


@pytest.mark.django_db
def test_counters_fetching(anti_tether_setup):
    hotspot = anti_tether_setup['hotspot_a']
    mock_mangle = [{
        '.id': '*1',
        'comment': TAG_TTL_LOCK,
        'action': 'change-ttl',
        'disabled': 'false',
        'packets': '1500',
        'bytes': '250000',
    }]
    mock_filter = [
        {'.id': '*2', 'comment': TAG_TTL_63, 'action': 'drop', 'disabled': 'false', 'packets': '40', 'bytes': '2800'},
        {'.id': '*3', 'comment': TAG_TTL_127, 'action': 'drop', 'disabled': 'false', 'packets': '10', 'bytes': '700'},
    ]

    mock_client = MockRouterOSClient(reachable=True, mangle_rules=mock_mangle, filter_rules=mock_filter)
    counters = get_anti_tethering_counters(hotspot, client_factory=lambda: mock_client)

    assert counters['router_reachable'] is True
    assert counters['ttl_lock']['packets'] == 1500
    assert counters['ttl_lock']['bytes'] == 250000
    assert counters['ttl_63']['packets'] == 40
    assert counters['ttl_127']['packets'] == 10
    assert counters['total_blocked_packets'] == 50
    assert counters['total_blocked_bytes'] == 3500


@pytest.mark.django_db
def test_api_tenant_isolation(anti_tether_setup):
    setup = anti_tether_setup
    client = APIClient()
    client.force_authenticate(user=setup['user_b'])

    # User B attempting to GET Hotspot A's anti-tethering policy must be forbidden
    resp = client.get(f"/api/v1/hotspots/{setup['hotspot_a'].id}/anti-tethering/")
    assert resp.status_code == 403

    # User B attempting to PATCH Hotspot A's policy must be forbidden
    patch_resp = client.patch(
        f"/api/v1/hotspots/{setup['hotspot_a'].id}/anti-tethering/",
        {'enabled': False},
        format='json'
    )
    assert patch_resp.status_code == 403


@pytest.mark.django_db
def test_api_get_and_patch_policy(anti_tether_setup, monkeypatch):
    setup = anti_tether_setup
    client = APIClient()
    client.force_authenticate(user=setup['user_a'])

    mock_client = MockRouterOSClient(reachable=True)
    monkeypatch.setattr(
        'apps.companies.services.anti_tethering_services.RouterOSAPIClient',
        lambda *args, **kwargs: mock_client
    )

    # GET
    resp = client.get(f"/api/v1/hotspots/{setup['hotspot_a'].id}/anti-tethering/")
    assert resp.status_code == 200
    assert resp.data['enabled'] is True
    assert resp.data['ttl_lock_value'] == 1
    assert 'router_status' in resp.data

    # PATCH with sync=false
    patch_resp = client.patch(
        f"/api/v1/hotspots/{setup['hotspot_a'].id}/anti-tethering/?sync=false",
        {'ttl_lock_value': 2, 'detect_ttl_127': False},
        format='json'
    )
    assert patch_resp.status_code == 200
    assert patch_resp.data['ttl_lock_value'] == 2
    assert patch_resp.data['detect_ttl_127'] is False

    # Check AuditLog
    audit = AuditLog.objects.filter(
        company=setup['company_a'],
        action='ANTI_TETHERING_POLICY_UPDATED'
    ).first()
    assert audit is not None
    assert audit.changes['after']['ttl_lock_value'] == 2


@pytest.mark.django_db
def test_api_restore_defaults(anti_tether_setup, monkeypatch):
    setup = anti_tether_setup
    client = APIClient()
    client.force_authenticate(user=setup['user_a'])

    # Set non-default value
    policy = get_or_create_anti_tethering_policy(setup['hotspot_a'])
    policy.enabled = False
    policy.ttl_lock_value = 5
    policy.save()

    # Mock sync to avoid physical socket connection
    mock_client = MockRouterOSClient(reachable=True)
    monkeypatch.setattr(
        'apps.companies.services.anti_tethering_services.RouterOSAPIClient',
        lambda *args, **kwargs: mock_client
    )

    resp = client.post(f"/api/v1/hotspots/{setup['hotspot_a'].id}/anti-tethering/restore-defaults/")
    assert resp.status_code == 200
    policy.refresh_from_db()
    assert policy.enabled is True
    assert policy.ttl_lock_value == 1
    assert policy.detect_ttl_63 is True
    assert policy.detect_ttl_127 is True
