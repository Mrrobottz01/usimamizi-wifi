import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from apps.audit.models import AuditLog
from apps.routers.services.router_client import RouterOSAPIClient, RouterOSError
from ..models import AntiTetheringPolicy, Company, HotspotConfiguration, IPv6Policy
from .uplink_services import (
    ROUTER_API_PORT,
    ROUTER_IP_DEFAULT,
    ROUTER_PASS_DEFAULT,
    ROUTER_USER_DEFAULT,
)

logger = logging.getLogger(__name__)

# Canonical rule tags
TAG_TTL_LOCK = "USIMAMIZI_ANTI_TETHER_TTL_LOCK"
TAG_TTL_63 = "USIMAMIZI_ANTI_TETHER_TTL63"
TAG_TTL_127 = "USIMAMIZI_ANTI_TETHER_TTL127"

# Legacy comment markers for backward-compatible adoption
LEGACY_TTL_LOCK_MARKERS = ["Anti-Tethering (Block Hotspot Sharing)", "Anti-Tethering"]
LEGACY_TTL_63_MARKERS = ["Anti-Tethering Drop forwarded client packets (TTL 63)", "TTL 63"]
LEGACY_TTL_127_MARKERS = ["Anti-Tethering Drop forwarded client packets (TTL 127)", "TTL 127"]

SERVER_IP_EXCLUDE = "10.5.50.254"
DEFAULT_INTERFACE = "bridgeLocal"


def get_router_credentials(hotspot: Optional[HotspotConfiguration] = None) -> Tuple[str, int, str, str]:
    if hotspot and getattr(hotspot, 'router', None) and hotspot.router.has_credentials:
        router = hotspot.router
        return str(router.management_ip), router.api_port, router.api_username, router.api_password

    host = os.getenv('MIKROTIK_HOST', ROUTER_IP_DEFAULT)
    port = int(os.getenv('MIKROTIK_PORT', str(ROUTER_API_PORT)))
    user = os.getenv('MIKROTIK_USER', ROUTER_USER_DEFAULT)
    password = os.getenv('MIKROTIK_PASSWORD', ROUTER_PASS_DEFAULT)
    return host, port, user, password


def get_or_create_anti_tethering_policy(hotspot: HotspotConfiguration) -> AntiTetheringPolicy:
    """
    Retrieve or initialize the Anti-Tethering policy for a HotSpot.
    """
    policy, _ = AntiTetheringPolicy.objects.get_or_create(
        hotspot=hotspot,
        defaults={
            'company': hotspot.company,
            'enabled': True,
            'max_devices': 1,
            'simultaneous_sessions': 1,
            'ttl_lock_enabled': True,
            'ttl_lock_value': 1,
            'detect_ttl_63': True,
            'detect_ttl_127': True,
            'strict_mode': False,
            'ipv6_policy': IPv6Policy.DISABLED,
        }
    )
    return policy


def _is_legacy_ttl_lock(comment: str) -> bool:
    return any(marker.lower() in comment.lower() for marker in LEGACY_TTL_LOCK_MARKERS)


def _is_legacy_ttl_63(comment: str) -> bool:
    return any(marker.lower() in comment.lower() for marker in LEGACY_TTL_63_MARKERS)


def _is_legacy_ttl_127(comment: str) -> bool:
    return any(marker.lower() in comment.lower() for marker in LEGACY_TTL_127_MARKERS)


def get_hotspot_rule_tag(base_tag: str, hotspot: HotspotConfiguration) -> str:
    return f"{base_tag}:{hotspot.id}"


def matches_ttl_lock_tag(comment: str, hotspot: HotspotConfiguration) -> bool:
    if comment == get_hotspot_rule_tag(TAG_TTL_LOCK, hotspot):
        return True
    if getattr(hotspot, 'is_default', False) or (hasattr(hotspot, 'company') and hotspot.company.hotspots.count() <= 1):
        return comment == TAG_TTL_LOCK or _is_legacy_ttl_lock(comment)
    return False


def matches_ttl_63_tag(comment: str, hotspot: HotspotConfiguration) -> bool:
    if comment == get_hotspot_rule_tag(TAG_TTL_63, hotspot):
        return True
    if getattr(hotspot, 'is_default', False) or (hasattr(hotspot, 'company') and hotspot.company.hotspots.count() <= 1):
        return comment == TAG_TTL_63 or _is_legacy_ttl_63(comment)
    return False


def matches_ttl_127_tag(comment: str, hotspot: HotspotConfiguration) -> bool:
    if comment == get_hotspot_rule_tag(TAG_TTL_127, hotspot):
        return True
    if getattr(hotspot, 'is_default', False) or (hasattr(hotspot, 'company') and hotspot.company.hotspots.count() <= 1):
        return comment == TAG_TTL_127 or _is_legacy_ttl_127(comment)
    return False


def get_anti_tethering_status(
    hotspot: HotspotConfiguration,
    client_factory=None
) -> Dict[str, Any]:
    """
    Query RouterOS live and evaluate policy synchronization state.
    """
    policy = get_or_create_anti_tethering_policy(hotspot)
    host, port, user, password = get_router_credentials(hotspot)

    res: Dict[str, Any] = {
        'status': 'UNKNOWN',
        'router_reachable': False,
        'ttl_lock_active': False,
        'ttl_63_active': False,
        'ttl_127_active': False,
        'rules_found': 0,
        'last_synced_at': policy.last_synced_at.isoformat() if policy.last_synced_at else None,
        'details': {},
        'error': None,
    }

    client = None
    try:
        if client_factory:
            client = client_factory()
        elif getattr(hotspot, 'router', None) and hotspot.router.has_credentials:
            client = RouterOSAPIClient.for_router(hotspot.router, timeout=3.0)
        else:
            client = RouterOSAPIClient(host=host, port=port, user=user, password=password, timeout=3.0)
        client.connect()
        res['router_reachable'] = True

        # Check mangle rule for TTL lock
        mangle_rules = client.query('/ip/firewall/mangle/print')
        for r in mangle_rules:
            comment = r.get('comment', '')
            if matches_ttl_lock_tag(comment, hotspot):
                res['rules_found'] += 1
                if r.get('disabled') != 'true' and r.get('action') == 'change-ttl':
                    res['ttl_lock_active'] = True
                    res['details']['ttl_lock'] = {
                        'id': r.get('.id'),
                        'new_ttl': r.get('new-ttl'),
                        'packets': int(r.get('packets', 0)),
                        'bytes': int(r.get('bytes', 0)),
                    }
                break

        # Check filter rules for TTL drops
        filter_rules = client.query('/ip/firewall/filter/print')
        for r in filter_rules:
            comment = r.get('comment', '')
            if matches_ttl_63_tag(comment, hotspot):
                res['rules_found'] += 1
                if r.get('disabled') != 'true' and r.get('action') == 'drop':
                    res['ttl_63_active'] = True
                    res['details']['ttl_63'] = {
                        'id': r.get('.id'),
                        'packets': int(r.get('packets', 0)),
                        'bytes': int(r.get('bytes', 0)),
                    }
            elif matches_ttl_127_tag(comment, hotspot):
                res['rules_found'] += 1
                if r.get('disabled') != 'true' and r.get('action') == 'drop':
                    res['ttl_127_active'] = True
                    res['details']['ttl_127'] = {
                        'id': r.get('.id'),
                        'packets': int(r.get('packets', 0)),
                        'bytes': int(r.get('bytes', 0)),
                    }

        # Calculate high-level status state
        if not policy.enabled:
            if res['ttl_lock_active'] or res['ttl_63_active'] or res['ttl_127_active']:
                res['status'] = 'OUT_OF_SYNC'
            else:
                res['status'] = 'DISABLED'
        else:
            expected_ttl_lock = policy.ttl_lock_enabled
            expected_63 = policy.detect_ttl_63
            expected_127 = policy.detect_ttl_127

            matches_ttl_lock = (res['ttl_lock_active'] == expected_ttl_lock)
            matches_63 = (res['ttl_63_active'] == expected_63)
            matches_127 = (res['ttl_127_active'] == expected_127)

            if matches_ttl_lock and matches_63 and matches_127:
                res['status'] = 'ACTIVE'
            elif res['ttl_lock_active'] or res['ttl_63_active'] or res['ttl_127_active']:
                res['status'] = 'PARTIALLY_ACTIVE'
            else:
                res['status'] = 'OUT_OF_SYNC'

    except Exception as e:
        logger.warning(f"Error querying anti-tethering status from RouterOS: {e}")
        res['status'] = 'ROUTER_UNREACHABLE'
        res['error'] = str(e)
    finally:
        if client:
            client.close()

    return res


def get_anti_tethering_counters(
    hotspot: HotspotConfiguration,
    client_factory=None
) -> Dict[str, Any]:
    """
    Fetch live packet and byte counters from RouterOS for anti-tethering rules.
    """
    host, port, user, password = get_router_credentials(hotspot)
    counters: Dict[str, Any] = {
        'ttl_lock': {'packets': 0, 'bytes': 0, 'active': False},
        'ttl_63': {'packets': 0, 'bytes': 0, 'active': False},
        'ttl_127': {'packets': 0, 'bytes': 0, 'active': False},
        'total_blocked_packets': 0,
        'total_blocked_bytes': 0,
        'router_reachable': False,
    }

    client = None
    try:
        if client_factory:
            client = client_factory()
        elif getattr(hotspot, 'router', None) and hotspot.router.has_credentials:
            client = RouterOSAPIClient.for_router(hotspot.router, timeout=3.0)
        else:
            client = RouterOSAPIClient(host=host, port=port, user=user, password=password, timeout=3.0)
        client.connect()
        counters['router_reachable'] = True

        mangle_rules = client.query('/ip/firewall/mangle/print')
        for r in mangle_rules:
            comment = r.get('comment', '')
            if matches_ttl_lock_tag(comment, hotspot):
                counters['ttl_lock'] = {
                    'packets': int(r.get('packets', 0)),
                    'bytes': int(r.get('bytes', 0)),
                    'active': r.get('disabled') != 'true',
                }
                break

        filter_rules = client.query('/ip/firewall/filter/print')
        for r in filter_rules:
            comment = r.get('comment', '')
            if matches_ttl_63_tag(comment, hotspot):
                pkts = int(r.get('packets', 0))
                bts = int(r.get('bytes', 0))
                counters['ttl_63'] = {
                    'packets': pkts,
                    'bytes': bts,
                    'active': r.get('disabled') != 'true',
                }
                counters['total_blocked_packets'] += pkts
                counters['total_blocked_bytes'] += bts
            elif matches_ttl_127_tag(comment, hotspot):
                pkts = int(r.get('packets', 0))
                bts = int(r.get('bytes', 0))
                counters['ttl_127'] = {
                    'packets': pkts,
                    'bytes': bts,
                    'active': r.get('disabled') != 'true',
                }
                counters['total_blocked_packets'] += pkts
                counters['total_blocked_bytes'] += bts

    except Exception as e:
        logger.warning(f"Error reading anti-tethering counters from RouterOS: {e}")
    finally:
        if client:
            client.close()

    return counters


def apply_anti_tethering_policy(
    policy: AntiTetheringPolicy,
    hotspot: HotspotConfiguration,
    client_factory=None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Idempotently sync and enforce Anti-Tethering rules on RouterOS.
    Adopts existing legacy rules without creating duplicates.
    """
    host, port, user, password = get_router_credentials(hotspot)
    client = None

    try:
        if client_factory:
            client = client_factory()
        elif getattr(hotspot, 'router', None) and hotspot.router.has_credentials:
            client = RouterOSAPIClient.for_router(hotspot.router, timeout=4.0)
        else:
            client = RouterOSAPIClient(host=host, port=port, user=user, password=password, timeout=4.0)
        client.connect()

        # Step 1: Pre-flight interface check
        interfaces = client.query('/interface/print')
        interface_names = [i.get('name') for i in interfaces]
        configured_iface = getattr(hotspot, 'interface_name', None) or DEFAULT_INTERFACE
        if configured_iface in interface_names:
            target_interface = configured_iface
        elif DEFAULT_INTERFACE in interface_names:
            target_interface = DEFAULT_INTERFACE
        else:
            target_interface = interface_names[0] if interface_names else 'bridgeLocal'

        tag_ttl_lock = get_hotspot_rule_tag(TAG_TTL_LOCK, hotspot)
        tag_ttl_63 = get_hotspot_rule_tag(TAG_TTL_63, hotspot)
        tag_ttl_127 = get_hotspot_rule_tag(TAG_TTL_127, hotspot)

        # Step 2: Manage TTL Lock in /ip/firewall/mangle
        existing_mangle = client.query('/ip/firewall/mangle/print')
        ttl_lock_rule = None
        for r in existing_mangle:
            comment = r.get('comment', '')
            if matches_ttl_lock_tag(comment, hotspot):
                ttl_lock_rule = r
                break

        if policy.enabled and policy.ttl_lock_enabled:
            expected_new_ttl = f"set:{policy.ttl_lock_value}"
            if ttl_lock_rule:
                # Update comment and parameters if needed
                rule_id = ttl_lock_rule['.id']
                client.execute('/ip/firewall/mangle/set', [
                    f'=.id={rule_id}',
                    f'=comment={tag_ttl_lock}',
                    f'=new-ttl={expected_new_ttl}',
                    '=disabled=false',
                    f'=out-interface={target_interface}',
                    f'=dst-address=!{SERVER_IP_EXCLUDE}',
                    '=action=change-ttl',
                    '=passthrough=yes',
                ])
            else:
                client.execute('/ip/firewall/mangle/add', [
                    '=chain=postrouting',
                    f'=out-interface={target_interface}',
                    f'=dst-address=!{SERVER_IP_EXCLUDE}',
                    '=action=change-ttl',
                    f'=new-ttl={expected_new_ttl}',
                    '=passthrough=yes',
                    f'=comment={tag_ttl_lock}',
                    '=disabled=false',
                ])
        else:
            if ttl_lock_rule:
                rid = ttl_lock_rule['.id']
                client.execute('/ip/firewall/mangle/remove', [f'=.id={rid}'])

        # Step 3: Manage TTL 63 Drop in /ip/firewall/filter
        existing_filter = client.query('/ip/firewall/filter/print')
        ttl_63_rule = None
        ttl_127_rule = None
        for r in existing_filter:
            comment = r.get('comment', '')
            if matches_ttl_63_tag(comment, hotspot):
                ttl_63_rule = r
            elif matches_ttl_127_tag(comment, hotspot):
                ttl_127_rule = r

        if policy.enabled and policy.detect_ttl_63:
            if ttl_63_rule:
                rid = ttl_63_rule['.id']
                client.execute('/ip/firewall/filter/set', [
                    f'=.id={rid}',
                    f'=comment={tag_ttl_63}',
                    '=ttl=equal:63',
                    f'=in-interface={target_interface}',
                    '=action=drop',
                    '=disabled=false',
                ])
            else:
                client.execute('/ip/firewall/filter/add', [
                    '=chain=forward',
                    f'=in-interface={target_interface}',
                    '=ttl=equal:63',
                    '=action=drop',
                    f'=comment={tag_ttl_63}',
                    '=disabled=false',
                ])
        else:
            if ttl_63_rule:
                rid = ttl_63_rule['.id']
                client.execute('/ip/firewall/filter/remove', [f'=.id={rid}'])

        # Step 4: Manage TTL 127 Drop in /ip/firewall/filter
        if policy.enabled and policy.detect_ttl_127:
            if ttl_127_rule:
                rid = ttl_127_rule['.id']
                client.execute('/ip/firewall/filter/set', [
                    f'=.id={rid}',
                    f'=comment={tag_ttl_127}',
                    '=ttl=equal:127',
                    f'=in-interface={target_interface}',
                    '=action=drop',
                    '=disabled=false',
                ])
            else:
                client.execute('/ip/firewall/filter/add', [
                    '=chain=forward',
                    f'=in-interface={target_interface}',
                    '=ttl=equal:127',
                    '=action=drop',
                    f'=comment={tag_ttl_127}',
                    '=disabled=false',
                ])
        else:
            if ttl_127_rule:
                rid = ttl_127_rule['.id']
                client.execute('/ip/firewall/filter/remove', [f'=.id={rid}'])

        return True, "Anti-Tethering policy applied successfully.", {}

    except Exception as e:
        logger.error(f"Failed to apply anti-tethering policy to RouterOS: {e}")
        return False, str(e), {}
    finally:
        if client:
            client.close()


def remove_anti_tethering_policy(
    hotspot: HotspotConfiguration,
    client_factory=None
) -> Tuple[bool, str]:
    """
    Remove all Usimamizi-managed anti-tethering rules from RouterOS.
    Leaves unrelated firewall rules completely untouched.
    """
    host, port, user, password = get_router_credentials(hotspot)
    client = None

    try:
        if client_factory:
            client = client_factory()
        elif getattr(hotspot, 'router', None) and hotspot.router.has_credentials:
            client = RouterOSAPIClient.for_router(hotspot.router, timeout=4.0)
        else:
            client = RouterOSAPIClient(host=host, port=port, user=user, password=password, timeout=4.0)
        client.connect()

        # Remove mangle rule
        mangles = client.query('/ip/firewall/mangle/print')
        for r in mangles:
            comment = r.get('comment', '')
            if matches_ttl_lock_tag(comment, hotspot):
                rid = r['.id']
                client.execute('/ip/firewall/mangle/remove', [f'=.id={rid}'])

        # Remove filter rules
        filters = client.query('/ip/firewall/filter/print')
        for r in filters:
            comment = r.get('comment', '')
            if matches_ttl_63_tag(comment, hotspot) or matches_ttl_127_tag(comment, hotspot):
                rid = r['.id']
                client.execute('/ip/firewall/filter/remove', [f'=.id={rid}'])

        return True, "Anti-Tethering rules removed from router."
    except Exception as e:
        logger.error(f"Failed to remove anti-tethering rules from RouterOS: {e}")
        return False, str(e)
    finally:
        if client:
            client.close()


def sync_anti_tethering_policy(
    hotspot: HotspotConfiguration,
    user=None,
    client_factory=None
) -> Dict[str, Any]:
    """
    Full reconciliation between database policy and RouterOS.
    Updates sync timestamps, caches status, and logs audit events.
    """
    policy = get_or_create_anti_tethering_policy(hotspot)
    success, message, _ = apply_anti_tethering_policy(policy, hotspot, client_factory=client_factory)

    live_status = get_anti_tethering_status(hotspot, client_factory=client_factory)
    now = timezone.now()

    if success:
        policy.last_synced_at = now
        policy.last_router_status = live_status
        policy.save(update_fields=['last_synced_at', 'last_router_status', 'updated_at'])

        AuditLog.objects.create(
            company=hotspot.company,
            user=user,
            action='ANTI_TETHERING_SYNCED',
            resource_type='HotspotConfiguration',
            resource_id=str(hotspot.id),
            changes={
                'status': live_status.get('status'),
                'enabled': policy.enabled,
                'ttl_lock_enabled': policy.ttl_lock_enabled,
                'detect_ttl_63': policy.detect_ttl_63,
                'detect_ttl_127': policy.detect_ttl_127,
                'result': 'SUCCESS',
            }
        )
    else:
        AuditLog.objects.create(
            company=hotspot.company,
            user=user,
            action='ANTI_TETHERING_SYNC_FAILED',
            resource_type='HotspotConfiguration',
            resource_id=str(hotspot.id),
            changes={'error': message, 'result': 'FAILED'}
        )

    return {
        'success': success,
        'message': message,
        'status': live_status.get('status'),
        'live_status': live_status,
        'policy': {
            'enabled': policy.enabled,
            'max_devices': policy.max_devices,
            'simultaneous_sessions': policy.simultaneous_sessions,
            'ttl_lock_enabled': policy.ttl_lock_enabled,
            'ttl_lock_value': policy.ttl_lock_value,
            'detect_ttl_63': policy.detect_ttl_63,
            'detect_ttl_127': policy.detect_ttl_127,
            'strict_mode': policy.strict_mode,
            'ipv6_policy': policy.ipv6_policy,
            'last_synced_at': policy.last_synced_at.isoformat() if policy.last_synced_at else None,
        }
    }


def restore_default_anti_tethering_policy(
    hotspot: HotspotConfiguration,
    user=None,
    client_factory=None
) -> Dict[str, Any]:
    """
    Restore recommended baseline settings and sync immediately with RouterOS.
    """
    policy = get_or_create_anti_tethering_policy(hotspot)
    policy.enabled = True
    policy.max_devices = 1
    policy.simultaneous_sessions = 1
    policy.ttl_lock_enabled = True
    policy.ttl_lock_value = 1
    policy.detect_ttl_63 = True
    policy.detect_ttl_127 = True
    policy.strict_mode = False
    policy.ipv6_policy = IPv6Policy.DISABLED
    policy.save()

    AuditLog.objects.create(
        company=hotspot.company,
        user=user,
        action='ANTI_TETHERING_DEFAULTS_RESTORED',
        resource_type='HotspotConfiguration',
        resource_id=str(hotspot.id),
        changes={'action': 'RESTORE_RECOMMENDED_DEFAULTS'}
    )

    return sync_anti_tethering_policy(hotspot, user=user, client_factory=client_factory)
