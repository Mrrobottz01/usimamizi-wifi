import errno
import logging
import socket
import ssl
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RouterOSError(Exception):
    """Base exception for RouterOS API operations with structured diagnostic code."""

    def __init__(self, code: str, message: str, original_exc: Optional[Exception] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.original_exc = original_exc

    def __str__(self):
        return f"[{self.code}] {self.message}"


class RouterOSAPIClient:
    """
    Hardened synchronous client for MikroTik RouterOS API (TCP 8728 plain / 8729 TLS).
    Supports per-router initialization, TLS encryption, and structured error taxonomy.
    """

    def __init__(
        self,
        host: str,
        port: int = 8728,
        user: str = '',
        password: str = '',
        use_tls: bool = False,
        timeout: float = 4.0,
        fallback_host: Optional[str] = None,
    ):
        self.host = host
        self.fallback_host = fallback_host
        self.port = int(port)
        self.user = user
        self.password = password
        self.use_tls = use_tls
        self.timeout = float(timeout)
        self.sock: Optional[socket.socket] = None

    @classmethod
    def for_router(cls, router, timeout: float = 4.0) -> 'RouterOSAPIClient':
        """
        Instantiate client directly from a Router model instance with decrypted credentials.
        Rejects connection attempts immediately if router credentials are not configured.
        Automatically enables fallback to router LAN gateway IP (e.g. 10.5.50.1).
        """
        if not router.has_credentials:
            raise RouterOSError(
                code='ROUTER_CREDENTIALS_NOT_CONFIGURED',
                message=(
                    f"Router '{router.name}' ({router.management_ip}) does not have management credentials "
                    "configured. Please set API username and password before connecting."
                ),
            )

        port = router.api_port or (8729 if router.use_tls else 8728)
        fallback_ip = getattr(router, 'fallback_management_ip', None) or '10.5.50.1'
        return cls(
            host=str(router.management_ip),
            fallback_host=str(fallback_ip) if fallback_ip else None,
            port=port,
            user=router.api_username,
            password=router.api_password,
            use_tls=bool(router.use_tls),
            timeout=timeout,
        )

    def _connect_socket(self, target_host: str, conn_timeout: float):
        """Establish raw TCP or TLS socket to target host with specific timeout."""
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(conn_timeout)
        try:
            if self.use_tls:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                self.sock = ctx.wrap_socket(raw_sock, server_hostname=target_host)
            else:
                self.sock = raw_sock

            self.sock.connect((target_host, self.port))
        except socket.timeout as exc:
            self.close()
            raise RouterOSError(
                code='CONNECTION_TIMEOUT',
                message=f"Connection to RouterOS at {target_host}:{self.port} timed out after {conn_timeout}s.",
                original_exc=exc,
            ) from exc
        except ConnectionRefusedError as exc:
            self.close()
            raise RouterOSError(
                code='CONNECTION_REFUSED',
                message=f"Connection refused by {target_host}:{self.port}. Ensure RouterOS API service is enabled.",
                original_exc=exc,
            ) from exc
        except ssl.SSLError as exc:
            self.close()
            raise RouterOSError(
                code='TLS_ERROR',
                message=f"TLS handshake failed connecting to {target_host}:{self.port}: {exc}",
                original_exc=exc,
            ) from exc
        except OSError as exc:
            self.close()
            if exc.errno in (errno.EHOSTUNREACH, errno.ENETUNREACH, 10065, 10051):
                code = 'HOST_UNREACHABLE'
            elif exc.errno in (errno.ECONNREFUSED, 10061):
                code = 'CONNECTION_REFUSED'
            elif exc.errno in (errno.ETIMEDOUT, 10060):
                code = 'CONNECTION_TIMEOUT'
            else:
                code = 'NETWORK_ERROR'
            raise RouterOSError(
                code=code,
                message=f"Network error connecting to {target_host}:{self.port}: {exc}",
                original_exc=exc,
            ) from exc
        except Exception as exc:
            self.close()
            raise RouterOSError(
                code='UNKNOWN_ERROR',
                message=f"Unexpected error connecting to {target_host}:{self.port}: {exc}",
                original_exc=exc,
            ) from exc

    def connect(self):
        """Establish TCP/TLS socket connection and authenticate with RouterOS API."""
        candidate_hosts = [self.host]
        if self.fallback_host and self.fallback_host != self.host:
            candidate_hosts.append(self.fallback_host)

        last_error = None
        for idx, candidate in enumerate(candidate_hosts):
            # For multi-host fallback, give the first host an agile 1.5s timeout so fallback is tried quickly
            cand_timeout = min(self.timeout, 1.5) if len(candidate_hosts) > 1 and idx == 0 else self.timeout
            try:
                self._connect_socket(candidate, cand_timeout)
                self.host = candidate
                last_error = None
                break
            except RouterOSError as exc:
                last_error = exc
                if idx < len(candidate_hosts) - 1:
                    logger.warning(
                        "Connecting to RouterOS at %s:%d failed (%s). Trying fallback candidate %s...",
                        candidate, self.port, exc.code, candidate_hosts[idx + 1]
                    )
                    continue
                raise last_error

        # Authenticate with RouterOS API
        try:
            self._send_sentence(['/login', f'=name={self.user}', f'=password={self.password}'])
            res = self._read_sentence()
            if not res:
                raise RouterOSError(
                    code='NO_RESPONSE',
                    message=f"RouterOS at {self.host}:{self.port} sent an empty response during login.",
                )
            if res[0] == '!done':
                return
            elif res[0] == '!trap':
                msg = next((x[9:] for x in res if x.startswith('=message=')), 'Authentication failed')
                raise RouterOSError(
                    code='AUTHENTICATION_FAILED',
                    message=f"RouterOS authentication failed on {self.host}:{self.port}: {msg}",
                )
            else:
                raise RouterOSError(
                    code='AUTHENTICATION_FAILED',
                    message=f"Unexpected login response from RouterOS {self.host}:{self.port}: {res}",
                )
        except RouterOSError:
            self.close()
            raise
        except socket.timeout as exc:
            self.close()
            raise RouterOSError(
                code='CONNECTION_TIMEOUT',
                message=f"Timeout waiting for login response from {self.host}:{self.port}.",
                original_exc=exc,
            ) from exc
        except Exception as exc:
            self.close()
            raise RouterOSError(
                code='AUTHENTICATION_FAILED',
                message=f"Error authenticating with {self.host}:{self.port}: {exc}",
                original_exc=exc,
            ) from exc

    def close(self):
        """Close open socket connection safely."""
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
            raise RouterOSError('NOT_CONNECTED', 'Cannot send sentence: socket is not connected.')
        for w in words:
            b = w.encode('utf-8')
            length = len(b)
            if length < 0x80:
                self.sock.send(bytes([length]))
            elif length < 0x4000:
                self.sock.send(bytes([length >> 8 | 0x80, length & 0xFF]))
            elif length < 0x200000:
                self.sock.send(bytes([length >> 16 | 0xC0, (length >> 8) & 0xFF, length & 0xFF]))
            else:
                self.sock.send(bytes([0xF0, (length >> 24) & 0xFF, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF]))
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
            if length >= 0x80 and length < 0xC0:
                b2 = self.sock.recv(1)
                length = ((length & 0x7F) << 8) | b2[0]
            elif length >= 0xC0 and length < 0xE0:
                b2 = self.sock.recv(1)
                b3 = self.sock.recv(1)
                length = ((length & 0x3F) << 16) | (b2[0] << 8) | b3[0]
            elif length >= 0xE0 and length < 0xF0:
                b2 = self.sock.recv(1)
                b3 = self.sock.recv(1)
                b4 = self.sock.recv(1)
                length = ((length & 0x1F) << 24) | (b2[0] << 16) | (b3[0] << 8) | b4[0]
            elif length == 0xF0:
                b1 = self.sock.recv(1)
                b2 = self.sock.recv(1)
                b3 = self.sock.recv(1)
                b4 = self.sock.recv(1)
                length = (b1[0] << 24) | (b2[0] << 16) | (b3[0] << 8) | b4[0]

            word_bytes = b''
            while len(word_bytes) < length:
                chunk = self.sock.recv(length - len(word_bytes))
                if not chunk:
                    break
                word_bytes += chunk
            res.append(word_bytes.decode('utf-8', errors='ignore'))
        return res

    def query(self, cmd: str, args: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Query RouterOS API command and return list of result dicts."""
        words = [cmd] + (args or [])
        self._send_sentence(words)
        results = []
        while True:
            line = self._read_sentence()
            if not line or line[0] in ['!done', '!trap']:
                if line and line[0] == '!trap':
                    msg = next((x[9:] for x in line if x.startswith('=message=')), 'Unknown trap error')
                    logger.warning(f"RouterOS query '{cmd}' trap: {msg}")
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
        """Execute a mutating RouterOS API command and return (success, message)."""
        words = [cmd] + (args or [])
        self._send_sentence(words)
        line = self._read_sentence()
        if line and line[0] == '!done':
            return True, 'OK'
        elif line and line[0] == '!trap':
            msg = next((x[9:] for x in line if x.startswith('=message=')), 'Error')
            return False, msg
        return True, 'OK'
