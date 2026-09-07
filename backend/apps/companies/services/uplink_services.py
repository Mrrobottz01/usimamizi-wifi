import logging
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from apps.routers.models import Router
from apps.routers.services.router_client import RouterOSAPIClient, RouterOSError
from ..models import Company, RouterUplinkProfile

logger = logging.getLogger(__name__)

ROUTER_IP_DEFAULT = '10.5.50.1'
ROUTER_API_PORT = 8728
ROUTER_USER_DEFAULT = 'admin'
ROUTER_PASS_DEFAULT = 'admin'


def _resolve_router_and_client(
    router: Optional[Router] = None,
    router_ip: Optional[str] = None,
    company: Optional[Company] = None,
    timeout: float = 4.0,
) -> Tuple[Optional[Router], str, str, RouterOSAPIClient]:
    """
    Resolve target Router, uplink interface name, management IP, and an initialized RouterOSAPIClient.
    Prefers explicit router instance; falls back to router_ip lookup or company's online/reachable router.
    """
    target_router = router
    ip = router_ip

    if not target_router and router_ip:
        target_router = Router.objects.filter(management_ip=router_ip).first()

    if not target_router and company:
        # Prefer ONLINE router first, then router with credentials, then most recently updated active router
        target_router = (
            company.routers.filter(is_active=True, health_status='ONLINE').first()
            or company.routers.filter(is_active=True, has_credentials=True).first()
            or company.routers.filter(is_active=True).order_by('-updated_at').first()
        )

    if target_router:
        ip = str(target_router.management_ip)
        interface_name = target_router.uplink_interface_name or 'wlan2'
        fallback_ip = getattr(target_router, 'fallback_management_ip', None) or '10.5.50.1'
        if target_router.has_credentials:
            client = RouterOSAPIClient.for_router(target_router, timeout=timeout)
        else:
            client = RouterOSAPIClient(
                host=ip,
                fallback_host=fallback_ip,
                port=target_router.api_port,
                user=target_router.api_username or ROUTER_USER_DEFAULT,
                password=target_router.api_password or ROUTER_PASS_DEFAULT,
                use_tls=target_router.use_tls,
                timeout=timeout,
            )
    else:
        ip = ip or ROUTER_IP_DEFAULT
        interface_name = 'wlan2'
        client = RouterOSAPIClient(
            host=ip,
            port=ROUTER_API_PORT,
            user=ROUTER_USER_DEFAULT,
            password=ROUTER_PASS_DEFAULT,
            timeout=timeout,
        )

    return target_router, interface_name, ip, client


def get_router_uplink_status(
    router: Optional[Router] = None,
    router_ip: str = ROUTER_IP_DEFAULT,
    company: Optional[Company] = None,
) -> Dict[str, Any]:
    target_router, interface_name, ip, client = _resolve_router_and_client(
        router=router,
        router_ip=router_ip,
        company=company,
        timeout=3.0,
    )

    status: Dict[str, Any] = {
        'connected': False,
        'ssid': '',
        'signal_strength': 'N/A',
        'wan_ip': 'N/A',
        'gateway': 'N/A',
        'internet_online': False,
        'latency_ms': None,
        'interface_name': interface_name,
        'mode': 'station',
        'router_id': str(target_router.id) if target_router else None,
        'router_name': target_router.name if target_router else None,
        'management_ip': ip,
        'error': None,
    }

    try:
        with client:
            wireless_info = client.query('/interface/wireless/print', [f'?name={interface_name}', '=detail='])
            if wireless_info:
                wlan = wireless_info[0]
                status['ssid'] = wlan.get('ssid', '')
                status['interface_name'] = wlan.get('name', interface_name)
                status['connected'] = (wlan.get('running') == 'true')
                status['mode'] = wlan.get('mode', 'station')

            reg_info = client.query('/interface/wireless/registration-table/print', [f'?interface={interface_name}'])
            if reg_info:
                status['signal_strength'] = reg_info[0].get('signal-strength', 'N/A')

            dhcp_info = client.query('/ip/dhcp-client/print', [f'?interface={interface_name}', '=detail='])
            if dhcp_info:
                dhcp = dhcp_info[0]
                status['wan_ip'] = dhcp.get('address', 'N/A')
                status['gateway'] = dhcp.get('gateway', 'N/A')

                # Auto-sync dynamic WAN management_ip only if router is NOT using a private management tunnel (10.8.0.x or 10.5.50.x)
                raw_ip = dhcp.get('address', '').split('/')[0].strip()
                is_tunnel_ip = target_router and (
                    str(target_router.management_ip).startswith('10.8.')
                    or str(target_router.management_ip).startswith('10.5.50.')
                )
                if raw_ip and raw_ip != 'N/A' and target_router and target_router.management_ip != raw_ip and not is_tunnel_ip:
                    try:
                        logger.info("Auto-syncing router %s management_ip: %s -> %s", target_router.name, target_router.management_ip, raw_ip)
                        target_router.management_ip = raw_ip
                        target_router.save(update_fields=['management_ip', 'updated_at'])
                        status['management_ip'] = raw_ip
                    except Exception:
                        pass

            try:
                ping_info = client.query('/ping', ['=address=8.8.8.8', '=count=2'])
                if ping_info and any(p.get('received') != '0' for p in ping_info):
                    status['internet_online'] = True
                    latencies = [p.get('time') for p in ping_info if p.get('time')]
                    status['latency_ms'] = latencies[0] if latencies else 'OK'
            except Exception:
                status['internet_online'] = False

    except Exception as e:
        logger.error('Error querying MikroTik uplink status on %s: %s', ip, e)
        status['error'] = str(e)

    return status


def scan_nearby_networks(
    router: Optional[Router] = None,
    router_ip: str = ROUTER_IP_DEFAULT,
    duration_seconds: int = 4,
) -> List[Dict[str, Any]]:
    """
    Scan for nearby wireless networks across 2.4 GHz and 5 GHz spectrum.
    Queries the target RouterOS wireless interface directly via API.
    """
    networks: Dict[str, Dict[str, Any]] = {}

    # Query RouterOS wireless scan if router is reachable
    try:
        target_router, interface_name, ip, client = _resolve_router_and_client(
            router=router,
            router_ip=router_ip,
            timeout=8.0,
        )
        with client:
            # Query active wireless interfaces from router
            wlan_candidates = []
            try:
                wlan_list = client.query('/interface/wireless/print')
                for w in wlan_list:
                    name = w.get('name')
                    # Station mode interfaces are primary scan candidates
                    if name:
                        wlan_candidates.append(name)
            except Exception:
                pass

            if not wlan_candidates:
                # Default to wlan2 (5GHz uplink) if not dynamically queried
                wlan_candidates = ['wlan2']

            for wlan_iface in wlan_candidates:
                try:
                    # RouterOS API scan: /interface/wireless/scan with =.id=<wlan_name>
                    client._send_sentence(['/interface/wireless/scan', f'=.id={wlan_iface}'])
                    start_t = time.time()
                    while time.time() - start_t < 3.0:
                        try:
                            line = client._read_sentence()
                            if not line or line[0] in ['!done', '!trap']:
                                break
                            if line[0] == '!re':
                                d = dict(x[1:].split('=', 1) for x in line[1:] if x.startswith('=') and '=' in x[1:])
                                ssid = d.get('ssid')
                                if ssid and ssid != 'Usimamizi-WiFi-Lab' and ssid not in networks:
                                    band = '5GHz' if 'wlan2' in wlan_iface or '5' in str(d.get('channel', '')) else '2.4GHz'
                                    networks[ssid] = {
                                        'ssid': ssid,
                                        'signal': d.get('sig', 'N/A'),
                                        'band': band,
                                        'frequency': d.get('channel', '') or d.get('frequency', '')
                                    }
                        except (socket.timeout, TimeoutError):
                            break
                except Exception as wlan_err:
                    logger.warning("Wireless scan on %s error: %s", wlan_iface, wlan_err)

    except Exception as e:
        logger.warning('RouterOS Wi-Fi scan error: %s', e)

    def parse_sig(val):
        try:
            return int(str(val).replace('%', '').split('@')[0].replace('dBm', '').strip())
        except Exception:
            return -999

    return sorted(list(networks.values()), key=lambda x: parse_sig(x['signal']), reverse=True)


@transaction.atomic
def restore_home_airtel(
    company: Company,
    router: Optional[Router] = None,
    router_ip: str = ROUTER_IP_DEFAULT,
) -> Dict[str, Any]:
    """
    Instantly restores station interface to the pre-configured working 'airtel-security' profile on MikroTik.
    """
    target_router, interface_name, ip, client = _resolve_router_and_client(
        router=router,
        router_ip=router_ip,
        company=company,
        timeout=4.0,
    )

    with client:
        wlan_info = client.query('/interface/wireless/print', [f'?name={interface_name}'])
        if wlan_info:
            wlan_id = wlan_info[0].get('.id')
            client.execute(
                '/interface/wireless/set',
                [
                    f'=.id={wlan_id}',
                    '=ssid=Avie_5G',
                    '=security-profile=airtel-security'
                ]
            )

        dhcp_info = client.query('/ip/dhcp-client/print', [f'?interface={interface_name}'])
        if dhcp_info:
            dhcp_id = dhcp_info[0].get('.id')
            client.execute('/ip/dhcp-client/release', [f'=.id={dhcp_id}'])

    time.sleep(3.5)

    if target_router:
        RouterUplinkProfile.objects.filter(company=company, router=target_router).update(is_active=False)
        profile, _ = RouterUplinkProfile.objects.update_or_create(
            company=company,
            ssid='Avie_5G',
            router=target_router,
            defaults={
                'name': 'Home Airtel 5G',
                'is_active': True
            }
        )
    else:
        RouterUplinkProfile.objects.filter(company=company).update(is_active=False)
        profile, _ = RouterUplinkProfile.objects.update_or_create(
            company=company,
            ssid='Avie_5G',
            defaults={
                'name': 'Home Airtel 5G',
                'router': target_router,
                'is_active': True
            }
        )

    new_status = get_router_uplink_status(router=target_router, router_ip=ip, company=company)
    new_status['active_profile_id'] = str(profile.id)
    new_status['active_profile_name'] = profile.name
    return new_status


@transaction.atomic
def switch_router_uplink(
    *,
    company: Company,
    ssid: str,
    password: str,
    profile_name: str = '',
    router: Optional[Router] = None,
    router_ip: str = ROUTER_IP_DEFAULT,
) -> Dict[str, Any]:
    clean_ssid = ssid.strip()
    clean_pwd = password.strip()
    label = profile_name.strip() or clean_ssid

    if not clean_ssid:
        raise ValueError('SSID cannot be empty.')

    target_router, interface_name, ip, client = _resolve_router_and_client(
        router=router,
        router_ip=router_ip,
        company=company,
        timeout=4.0,
    )

    # Fallback to existing airtel-security if Avie_5G without password
    if clean_ssid.lower() == 'avie_5g' and not clean_pwd:
        return restore_home_airtel(company=company, router=target_router, router_ip=ip)

    sec_profile_name = 'uplink-dynamic-sec'

    with client:
        existing_sec = client.query('/interface/wireless/security-profiles/print', [f'?name={sec_profile_name}'])
        sec_id = existing_sec[0].get('.id') if existing_sec else None
        if sec_id:
            client.execute(
                '/interface/wireless/security-profiles/set',
                [
                    f'=.id={sec_id}',
                    '=mode=dynamic-keys',
                    '=authentication-types=wpa2-psk',
                    '=unicast-ciphers=aes-ccm',
                    '=group-ciphers=aes-ccm',
                    f'=wpa2-pre-shared-key={clean_pwd}'
                ]
            )
        else:
            client.execute(
                '/interface/wireless/security-profiles/add',
                [
                    f'=name={sec_profile_name}',
                    '=mode=dynamic-keys',
                    '=authentication-types=wpa2-psk',
                    '=unicast-ciphers=aes-ccm',
                    '=group-ciphers=aes-ccm',
                    f'=wpa2-pre-shared-key={clean_pwd}'
                ]
            )

        wlan_info = client.query('/interface/wireless/print', [f'?name={interface_name}'])
        if not wlan_info:
            raise RuntimeError(f'MikroTik does not have an upstream interface named {interface_name}.')

        wlan_id = wlan_info[0].get('.id')
        client.execute(
            '/interface/wireless/set',
            [
                f'=.id={wlan_id}',
                f'=ssid={clean_ssid}',
                f'=security-profile={sec_profile_name}'
            ]
        )

        try:
            dhcp_info = client.query('/ip/dhcp-client/print', [f'?interface={interface_name}'])
            if dhcp_info:
                dhcp_id = dhcp_info[0].get('.id')
                client.execute('/ip/dhcp-client/release', [f'=.id={dhcp_id}'])
        except Exception as e:
            logger.info("DHCP release notice: %s", e)

    time.sleep(2.0)

    if target_router:
        RouterUplinkProfile.objects.filter(company=company, router=target_router).update(is_active=False)
        profile, _ = RouterUplinkProfile.objects.update_or_create(
            company=company,
            ssid=clean_ssid,
            router=target_router,
            defaults={
                'name': label,
                'password': clean_pwd,
                'is_active': True
            }
        )
    else:
        RouterUplinkProfile.objects.filter(company=company).update(is_active=False)
        profile, _ = RouterUplinkProfile.objects.update_or_create(
            company=company,
            ssid=clean_ssid,
            defaults={
                'name': label,
                'password': clean_pwd,
                'router': target_router,
                'is_active': True
            }
        )

    new_status = get_router_uplink_status(router=target_router, company=company)
    if not new_status.get('connected') and not new_status.get('error'):
        new_status['ssid'] = clean_ssid
        new_status['signal_strength'] = 'Associating...'
    new_status['active_profile_id'] = str(profile.id)
    new_status['active_profile_name'] = profile.name
    return new_status
