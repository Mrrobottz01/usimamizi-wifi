import logging
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from ..models import Company, RouterUplinkProfile

logger = logging.getLogger(__name__)

ROUTER_IP_DEFAULT = '10.5.50.1'
ROUTER_API_PORT = 8728
ROUTER_USER_DEFAULT = 'admin'
ROUTER_PASS_DEFAULT = 'admin'


class RouterOSAPIClient:
    def __init__(self, host: str = ROUTER_IP_DEFAULT, port: int = ROUTER_API_PORT, user: str = ROUTER_USER_DEFAULT, password: str = ROUTER_PASS_DEFAULT, timeout: float = 4.0):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
        self._send_sentence(['/login', f'=name={self.user}', f'=password={self.password}'])
        res = self._read_sentence()
        if not res or res[0] != '!done':
            raise RuntimeError(f'RouterOS API authentication failed: {res}')

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _send_sentence(self, words: List[str]):
        if not self.sock:
            raise RuntimeError('Socket is not connected.')
        for w in words:
            b = w.encode('utf-8')
            length = len(b)
            if length < 0x80:
                self.sock.send(bytes([length]))
            elif length < 0x4000:
                self.sock.send(bytes([length >> 8 | 0x80, length & 0xFF]))
            self.sock.send(b)
        self.sock.send(b'\x00')

    def _read_sentence(self) -> List[str]:
        if not self.sock:
            return []
        res = []
        while True:
            b = self.sock.recv(1)
            if not b or b[0] == 0:
                break
            length = b[0]
            if length >= 0x80:
                b2 = self.sock.recv(1)
                length = ((length & 0x7F) << 8) | b2[0]
            word_bytes = b''
            while len(word_bytes) < length:
                chunk = self.sock.recv(length - len(word_bytes))
                if not chunk:
                    break
                word_bytes += chunk
            res.append(word_bytes.decode('utf-8', errors='ignore'))
        return res

    def query(self, cmd: str, args: Optional[List[str]] = None) -> List[Dict[str, str]]:
        words = [cmd] + (args or [])
        self._send_sentence(words)
        results = []
        while True:
            line = self._read_sentence()
            if not line or line[0] in ['!done', '!trap']:
                break
            if line[0] == '!re':
                d: Dict[str, str] = {}
                for item in line[1:]:
                    if item.startswith('='):
                        parts = item[1:].split('=', 1)
                        if len(parts) == 2:
                            d[parts[0]] = parts[1]
                results.append(d)
        return results

    def execute(self, cmd: str, args: Optional[List[str]] = None) -> Tuple[bool, str]:
        words = [cmd] + (args or [])
        self._send_sentence(words)
        line = self._read_sentence()
        if line and line[0] == '!done':
            return True, 'OK'
        elif line and line[0] == '!trap':
            msg = next((x[9:] for x in line if x.startswith('=message=')), 'Error')
            return False, msg
        return True, 'OK'


def get_router_uplink_status(router_ip: str = ROUTER_IP_DEFAULT) -> Dict[str, Any]:
    status: Dict[str, Any] = {
        'connected': False,
        'ssid': '',
        'signal_strength': 'N/A',
        'wan_ip': 'N/A',
        'gateway': 'N/A',
        'internet_online': False,
        'latency_ms': None,
        'interface_name': 'wlan2',
        'mode': 'station',
        'error': None
    }

    try:
        with RouterOSAPIClient(host=router_ip) as client:
            wireless_info = client.query('/interface/wireless/print', ['?name=wlan2', '=detail='])
            if wireless_info:
                wlan = wireless_info[0]
                status['ssid'] = wlan.get('ssid', '')
                status['interface_name'] = wlan.get('name', 'wlan2')
                status['connected'] = (wlan.get('running') == 'true')
                status['mode'] = wlan.get('mode', 'station')

            reg_info = client.query('/interface/wireless/registration-table/print', ['?interface=wlan2'])
            if reg_info:
                status['signal_strength'] = reg_info[0].get('signal-strength', 'N/A')

            dhcp_info = client.query('/ip/dhcp-client/print', ['?interface=wlan2', '=detail='])
            if dhcp_info:
                dhcp = dhcp_info[0]
                status['wan_ip'] = dhcp.get('address', 'N/A')
                status['gateway'] = dhcp.get('gateway', 'N/A')

            try:
                ping_info = client.query('/ping', ['=address=8.8.8.8', '=count=2'])
                if ping_info and any(p.get('received') != '0' for p in ping_info):
                    status['internet_online'] = True
                    latencies = [p.get('time') for p in ping_info if p.get('time')]
                    status['latency_ms'] = latencies[0] if latencies else 'OK'
            except Exception:
                status['internet_online'] = False

    except Exception as e:
        logger.error('Error querying MikroTik uplink status: %s', e)
        status['error'] = str(e)

    return status


def scan_nearby_networks(router_ip: str = ROUTER_IP_DEFAULT, duration_seconds: int = 4) -> List[Dict[str, Any]]:
    """
    Scan for nearby wireless networks across 2.4 GHz and 5 GHz spectrum.
    Uses native Wi-Fi hardware adapter scan for full spectrum discovery.
    """
    networks: Dict[str, Dict[str, Any]] = {}

    # 1. Native Wi-Fi spectrum scan (scans both 2.4 GHz and 5 GHz across all channels)
    try:
        import subprocess
        proc = subprocess.run(
            ['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
            capture_output=True,
            text=True,
            timeout=5
        )
        current_ssid = None
        current_signal = None
        current_band = None

        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith('SSID ') and ':' in line:
                current_ssid = line.split(':', 1)[1].strip()
            elif line.startswith('Signal') and ':' in line:
                current_signal = line.split(':', 1)[1].strip()
            elif line.startswith('Band') and ':' in line:
                current_band = line.split(':', 1)[1].strip()
                if current_ssid and current_ssid != 'Usimamizi-WiFi-Lab':
                    if current_ssid not in networks:
                        networks[current_ssid] = {
                            'ssid': current_ssid,
                            'signal': current_signal or 'N/A',
                            'band': current_band or '5GHz',
                            'frequency': ''
                        }
    except Exception as e:
        logger.warning('Native Wi-Fi scan error: %s', e)

    # 2. Query RouterOS wlan2 scan if router is reachable
    try:
        with RouterOSAPIClient(host=router_ip, timeout=3) as client:
            client._send_sentence(['/interface/wireless/scan', '=.tag=s1', '=numbers=wlan2', '=duration=2s'])
            start_t = time.time()
            while time.time() - start_t < 2.5:
                try:
                    line = client._read_sentence()
                    if not line or line[0] in ['!done', '!trap']:
                        break
                    if line[0] == '!re':
                        d = dict(x[1:].split('=', 1) for x in line[1:] if x.startswith('=') and '=' in x[1:])
                        ssid = d.get('ssid')
                        if ssid and ssid != 'Usimamizi-WiFi-Lab' and ssid not in networks:
                            networks[ssid] = {
                                'ssid': ssid,
                                'signal': d.get('sig', 'N/A'),
                                'band': d.get('band', '5GHz'),
                                'frequency': d.get('frequency', '')
                            }
                except socket.timeout:
                    break
            try:
                client._send_sentence(['/cancel', '=tag=s1'])
                client._read_sentence()
            except Exception:
                pass
    except Exception:
        pass

    def parse_sig(val):
        try:
            return int(val.replace('%', '').split('@')[0].replace('dBm', '').strip())
        except Exception:
            return -999

    return sorted(list(networks.values()), key=lambda x: parse_sig(x['signal']), reverse=True)



@transaction.atomic
def restore_home_airtel(company: Company, router_ip: str = ROUTER_IP_DEFAULT) -> Dict[str, Any]:
    """
    Instantly restores wlan2 to the pre-configured working 'airtel-security' profile on MikroTik.
    """
    with RouterOSAPIClient(host=router_ip) as client:
        wlan_info = client.query('/interface/wireless/print', ['?name=wlan2'])
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

        dhcp_info = client.query('/ip/dhcp-client/print', ['?interface=wlan2'])
        if dhcp_info:
            dhcp_id = dhcp_info[0].get('.id')
            client.execute('/ip/dhcp-client/release', [f'=.id={dhcp_id}'])

    time.sleep(3.5)

    RouterUplinkProfile.objects.filter(company=company).update(is_active=False)
    profile, _ = RouterUplinkProfile.objects.update_or_create(
        company=company,
        ssid='Avie_5G',
        defaults={
            'name': 'Home Airtel 5G',
            'is_active': True
        }
    )

    new_status = get_router_uplink_status(router_ip=router_ip)
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
    router_ip: str = ROUTER_IP_DEFAULT
) -> Dict[str, Any]:
    clean_ssid = ssid.strip()
    clean_pwd = password.strip()
    label = profile_name.strip() or clean_ssid

    if not clean_ssid:
        raise ValueError('SSID cannot be empty.')

    # Fallback to existing airtel-security if Avie_5G without password
    if clean_ssid.lower() == 'avie_5g' and not clean_pwd:
        return restore_home_airtel(company=company, router_ip=router_ip)

    sec_profile_name = 'uplink-dynamic-sec'

    with RouterOSAPIClient(host=router_ip) as client:
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

        wlan_info = client.query('/interface/wireless/print', ['?name=wlan2'])
        if not wlan_info:
            raise RuntimeError('MikroTik does not have an upstream interface named wlan2.')

        wlan_id = wlan_info[0].get('.id')
        client.execute(
            '/interface/wireless/set',
            [
                f'=.id={wlan_id}',
                f'=ssid={clean_ssid}',
                f'=security-profile={sec_profile_name}'
            ]
        )

        dhcp_info = client.query('/ip/dhcp-client/print', ['?interface=wlan2'])
        if dhcp_info:
            dhcp_id = dhcp_info[0].get('.id')
            client.execute('/ip/dhcp-client/release', [f'=.id={dhcp_id}'])

    time.sleep(3.5)

    RouterUplinkProfile.objects.filter(company=company).update(is_active=False)
    profile, _ = RouterUplinkProfile.objects.update_or_create(
        company=company,
        ssid=clean_ssid,
        defaults={
            'name': label,
            'password': clean_pwd,
            'is_active': True
        }
    )

    new_status = get_router_uplink_status(router_ip=router_ip)
    new_status['active_profile_id'] = str(profile.id)
    new_status['active_profile_name'] = profile.name
    return new_status
