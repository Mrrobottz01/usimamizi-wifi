import logging
import time
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings
from django.utils import timezone

from apps.companies.models import HotspotConfiguration
from apps.radius.models import RadiusClient
from apps.routers.models import Router, RouterHealthStatus
from .router_client import RouterOSAPIClient, RouterOSError
from .router_service import collect_router_telemetry

logger = logging.getLogger(__name__)

DEFAULT_RADIUS_SECRET = 'radius_shared_secret_lab'
DEFAULT_RADIUS_IP = '192.168.1.59'
DEFAULT_WALLED_GARDEN_DOMAINS = [
    'api.snippe.sh',
    'checkout.snippe.sh',
    'snippe.sh',
    'captive.apple.com',
    'connectivitycheck.gstatic.com',
    'www.msftconnecttest.com',
]


def _resolve_radius_config(router: Router, radius_ip: Optional[str] = None, shared_secret: Optional[str] = None) -> tuple[str, str]:
    secret = shared_secret
    ip = radius_ip

    if not secret:
        rc = getattr(router, 'radius_client', None)
        if not rc:
            rc = RadiusClient.objects.filter(router=router).first()
        if rc and rc.shared_secret:
            secret = rc.shared_secret
        else:
            secret = getattr(settings, 'RADIUS_DEFAULT_SHARED_SECRET', DEFAULT_RADIUS_SECRET)

    if not ip:
        ip = getattr(settings, 'RADIUS_SERVER_IP', None) or DEFAULT_RADIUS_IP

    return str(ip), str(secret)


def generate_router_bootstrap_script(
    router: Router,
    hotspot: Optional[HotspotConfiguration] = None,
    radius_server_ip: Optional[str] = None,
    shared_secret: Optional[str] = None,
    portal_base_url: Optional[str] = None,
    enable_anti_tethering: bool = True,
    enable_radius: bool = True,
    enable_hotspot: bool = True,
    enable_walled_garden: bool = True,
    walled_garden_domains: Optional[List[str]] = None,
) -> str:
    now_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    radius_ip, radius_sec = _resolve_radius_config(router, radius_server_ip, shared_secret)

    if not hotspot:
        hotspot = router.hotspots.filter(is_active=True).first()

    hs_interface = hotspot.interface_name if hotspot else 'bridgeLocal'
    hs_ssid = hotspot.ssid if hotspot else 'Usimamizi-WiFi-Lab'
    hs_server_name = hotspot.server_name if hotspot else 'hotspot1'
    hs_gateway = hotspot.gateway_ip if hotspot else '10.5.50.1'

    domains = list(walled_garden_domains or DEFAULT_WALLED_GARDEN_DOMAINS)
    if portal_base_url:
        import urllib.parse
        parsed = urllib.parse.urlparse(portal_base_url)
        if parsed.hostname and parsed.hostname not in domains:
            domains.append(parsed.hostname)

    lines: List[str] = [
        '#################################################################',
        '# USIMAMIZI WI-FI — AUTOMATED MIKROTIK PROVISIONING BOOTSTRAP   #',
        f'# Router:   {router.name} ({router.management_ip})',
        f'# Company:  {router.company.name if router.company else "Default"}',
        f'# Location: {router.location.name if router.location else "Unassigned"}',
        f'# Generated: {now_str}',
        '#################################################################',
        '',
        '# ---------------------------------------------------------------',
        '# 1. System Identity & Core Services',
        '# ---------------------------------------------------------------',
        f'/system identity set name="{router.identity or router.name}"',
        f'/ip service set api disabled=no port={router.api_port or 8728}',
        '/ip service set winbox disabled=no port=8291',
        ':do { /ip hotspot walled-garden ip add dst-port=8728-8729 protocol=tcp action=accept comment="Allow Usimamizi API on HotSpot" } on-error={}',
        ':do { /ip hotspot walled-garden ip add dst-port=8291 protocol=tcp action=accept comment="Allow WinBox on HotSpot" } on-error={}',
        '',
    ]

    if enable_radius:
        lines.extend([
            '# ---------------------------------------------------------------',
            '# 2. Central FreeRADIUS AAA & RFC 3576 CoA Client',
            '# ---------------------------------------------------------------',
            '# Enable Incoming CoA / Disconnect-Request on RFC 3576 port 3799',
            ':do { /radius incoming set accept=yes port=3799 } on-error={}',
            '',
            '# Clean old Usimamizi RADIUS entries and register new client',
            ':do { /radius remove [find comment~"Usimamizi"] } on-error={}',
            f'/radius add service=hotspot address={radius_ip} secret="{radius_sec}" \\',
            '    authentication-port=1812 accounting-port=1813 timeout=3000ms \\',
            f'    comment="Usimamizi Central AAA ({router.name})"',
            '',
        ])

    if enable_hotspot:
        lines.extend([
            '# ---------------------------------------------------------------',
            '# 3. HotSpot Server Profile & RADIUS Accounting Integration',
            '# ---------------------------------------------------------------',
            '# Enable RADIUS auth, accounting, and interim updates on HotSpot profile',
            '/ip hotspot profile set [find] \\',
            '    use-radius=yes \\',
            '    radius-accounting=yes \\',
            '    radius-interim-update=60s \\',
            '    login-by=http-chap,http-pap,cookie,mac-cookie \\',
            '    split-user-domain=no',
            '',
        ])

    if enable_walled_garden and domains:
        lines.extend([
            '# ---------------------------------------------------------------',
            '# 4. Payment Gateway & Portal Walled Garden Whitelist',
            '# ---------------------------------------------------------------',
            ':do { /ip hotspot walled-garden remove [find comment~"Usimamizi"] } on-error={}',
        ])
        for dom in domains:
            clean_dom = dom.strip()
            if clean_dom:
                lines.append(f'/ip hotspot walled-garden add dst-host="*{clean_dom}" action=allow comment="Usimamizi Walled Garden: {clean_dom}"')
        lines.append('')

    if enable_anti_tethering:
        lines.extend([
            '# ---------------------------------------------------------------',
            '# 5. Anti-Tethering & Wi-Fi HotSpot Sharing Prevention',
            '# ---------------------------------------------------------------',
            '# Layer 2: Mangle Postrouting TTL Lock (set TTL = 1 for client traffic)',
            ':do { /ip firewall mangle remove [find comment~"Usimamizi: Anti-Tethering"] } on-error={}',
            f'/ip firewall mangle add chain=postrouting out-interface={hs_interface} \\',
            '    action=change-ttl new-ttl=set:1 passthrough=yes \\',
            '    comment="Usimamizi: Anti-Tethering (Block Hotspot Sharing)"',
            '',
            '# Layer 3: Drop forwarded client packets arriving with decremented TTLs',
            ':do { /ip firewall filter remove [find comment~"Usimamizi: Anti-Tethering"] } on-error={}',
            f'/ip firewall filter add chain=forward in-interface={hs_interface} ttl=equal:63 action=drop \\',
            '    comment="Usimamizi: Anti-Tethering Drop forwarded client packets (TTL 63)"',
            f'/ip firewall filter add chain=forward in-interface={hs_interface} ttl=equal:127 action=drop \\',
            '    comment="Usimamizi: Anti-Tethering Drop forwarded client packets (TTL 127)"',
            '',
        ])

    lines.extend([
        '# ---------------------------------------------------------------',
        '# 6. Verification Status Check',
        '# ---------------------------------------------------------------',
        ':log info "Usimamizi provisioning script completed successfully."',
        '/radius print detail',
        '/ip hotspot print detail',
        '# END OF USIMAMIZI BOOTSTRAP SCRIPT',
        '',
    ])

    return '\n'.join(lines)


def provision_router_via_api(
    router: Router,
    options: Optional[Dict[str, Any]] = None,
    client_factory: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    opts = options or {}
    radius_ip, radius_sec = _resolve_radius_config(router, opts.get('radius_ip'), opts.get('shared_secret'))
    enable_anti_tethering = opts.get('enable_anti_tethering', True)
    enable_radius = opts.get('enable_radius', True)
    enable_hotspot = opts.get('enable_hotspot', True)
    enable_walled_garden = opts.get('enable_walled_garden', True)

    hotspot = router.hotspots.filter(is_active=True).first()
    hs_interface = hotspot.interface_name if hotspot else 'bridgeLocal'

    start_time = time.perf_counter()
    steps_log: List[Dict[str, Any]] = []

    def record_step(name: str, success: bool, message: str, details: Any = None):
        steps_log.append({
            'name': name,
            'success': success,
            'message': message,
            'details': details or {},
            'timestamp': timezone.now().isoformat(),
        })

    try:
        if client_factory:
            client = client_factory()
        else:
            client = RouterOSAPIClient.for_router(router, timeout=5.0)

        with client:
            # Step 1: Query System Identity & Verify Connectivity
            try:
                identities = client.query('/system/identity/print')
                curr_identity = identities[0].get('name') if identities else router.name
                record_step('connectivity', True, f"Connected to {router.management_ip} (Identity: {curr_identity})")
            except Exception as exc:
                record_step('connectivity', False, f"Failed querying system identity: {exc}")
                raise

            # Step 2: Ensure API Service Active
            try:
                services = client.query('/ip/service/print', ['?name=api'])
                if services:
                    api_id = services[0].get('.id')
                    client.execute('/ip/service/set', [f'=.id={api_id}', '=disabled=no', f'=port={router.api_port or 8728}'])
                record_step('api_service', True, f"API service verified on port {router.api_port or 8728}")
            except Exception as exc:
                record_step('api_service', False, f"Failed configuring API service: {exc}")

            # Step 3: Configure FreeRADIUS Client & Incoming CoA
            if enable_radius:
                try:
                    client.execute('/radius/incoming/set', ['=accept=yes', '=port=3799'])

                    existing_rad = client.query('/radius/print', ['?comment=Usimamizi Central AAA'])
                    if existing_rad:
                        rad_id = existing_rad[0].get('.id')
                        client.execute('/radius/set', [
                            f'=.id={rad_id}',
                            '=service=hotspot',
                            f'=address={radius_ip}',
                            f'=secret={radius_sec}',
                            '=authentication-port=1812',
                            '=accounting-port=1813',
                            '=timeout=3000ms',
                        ])
                    else:
                        client.execute('/radius/add', [
                            '=service=hotspot',
                            f'=address={radius_ip}',
                            f'=secret={radius_sec}',
                            '=authentication-port=1812',
                            '=accounting-port=1813',
                            '=timeout=3000ms',
                            '=comment=Usimamizi Central AAA',
                        ])
                    record_step('radius_client', True, f"RADIUS client registered pointing to {radius_ip}:1812/1813 with CoA port 3799")
                except Exception as exc:
                    record_step('radius_client', False, f"Failed configuring RADIUS client: {exc}")

            # Step 4: HotSpot Profile RADIUS Integration
            if enable_hotspot:
                try:
                    profiles = client.query('/ip/hotspot/profile/print')
                    if profiles:
                        for p in profiles:
                            p_id = p.get('.id')
                            client.execute('/ip/hotspot/profile/set', [
                                f'=.id={p_id}',
                                '=use-radius=yes',
                                '=radius-accounting=yes',
                                '=radius-interim-update=60s',
                            ])
                        record_step('hotspot_profile', True, f"Configured {len(profiles)} HotSpot profile(s) with RADIUS AAA & 60s accounting")
                    else:
                        record_step('hotspot_profile', True, "No HotSpot profiles found to update (service will need hotspot instance created)")
                except Exception as exc:
                    record_step('hotspot_profile', False, f"Failed configuring HotSpot profile: {exc}")

            # Step 5: Walled Garden Whitelist
            if enable_walled_garden:
                try:
                    domains = DEFAULT_WALLED_GARDEN_DOMAINS
                    added_count = 0
                    for dom in domains:
                        exists = client.query('/ip/hotspot/walled-garden/print', [f'?dst-host=*{dom}'])
                        if not exists:
                            client.execute('/ip/hotspot/walled-garden/add', [
                                f'=dst-host=*{dom}',
                                '=action=allow',
                                f'=comment=Usimamizi: {dom}',
                            ])
                            added_count += 1
                    record_step('walled_garden', True, f"Configured payment walled gardens ({added_count} new domains added, total {len(domains)})")
                except Exception as exc:
                    record_step('walled_garden', False, f"Failed configuring walled garden: {exc}")

            # Step 6: Anti-Tethering Firewall Rules
            if enable_anti_tethering:
                try:
                    mangles = client.query('/ip/firewall/mangle/print', ['?comment=Usimamizi: Anti-Tethering (Block Hotspot Sharing)'])
                    if not mangles:
                        client.execute('/ip/firewall/mangle/add', [
                            '=chain=postrouting',
                            f'=out-interface={hs_interface}',
                            '=action=change-ttl',
                            '=new-ttl=set:1',
                            '=passthrough=yes',
                            '=comment=Usimamizi: Anti-Tethering (Block Hotspot Sharing)',
                        ])

                    filters = client.query('/ip/firewall/filter/print', ['?comment~Usimamizi: Anti-Tethering'])
                    if not filters:
                        client.execute('/ip/firewall/filter/add', [
                            '=chain=forward',
                            f'=in-interface={hs_interface}',
                            '=ttl=equal:63',
                            '=action=drop',
                            '=comment=Usimamizi: Anti-Tethering Drop forwarded client packets (TTL 63)',
                        ])
                        client.execute('/ip/firewall/filter/add', [
                            '=chain=forward',
                            f'=in-interface={hs_interface}',
                            '=ttl=equal:127',
                            '=action=drop',
                            '=comment=Usimamizi: Anti-Tethering Drop forwarded client packets (TTL 127)',
                        ])
                    record_step('anti_tethering', True, f"Applied Anti-Tethering TTL-lock and forwarded filter drops on interface '{hs_interface}'")
                except Exception as exc:
                    record_step('anti_tethering', False, f"Failed applying anti-tethering firewall rules: {exc}")

    except RouterOSError as exc:
        record_step('execution_error', False, f"RouterOS API communication failed: {exc.message}")
    except Exception as exc:
        record_step('unexpected_error', False, f"Unexpected error during provisioning: {exc}")

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    telemetry = collect_router_telemetry(router, client_factory=client_factory)

    overall_success = all(s['success'] for s in steps_log if s['name'] in ('connectivity', 'api_service', 'radius_client', 'hotspot_profile'))

    resources = dict(router.system_resources or {})
    resources['provisioning'] = {
        'last_provisioned_at': timezone.now().isoformat(),
        'success': overall_success,
        'duration_ms': elapsed_ms,
        'steps_completed': [s['name'] for s in steps_log if s['success']],
    }
    router.system_resources = resources
    router.save(update_fields=['system_resources', 'updated_at'])

    return {
        'success': overall_success,
        'router_id': str(router.id),
        'router_name': router.name,
        'management_ip': str(router.management_ip),
        'health_status': router.health_status,
        'elapsed_ms': elapsed_ms,
        'steps': steps_log,
        'telemetry': telemetry,
    }
