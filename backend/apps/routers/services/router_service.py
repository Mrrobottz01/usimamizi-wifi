import logging
import time
from typing import Any, Callable, Dict, Optional

from django.utils import timezone

from apps.routers.models import Router, RouterHealthStatus
from .router_client import RouterOSAPIClient, RouterOSError

logger = logging.getLogger(__name__)


def set_router_credentials(
    router: Router,
    username: str,
    password: str,
    api_port: Optional[int] = None,
    use_tls: Optional[bool] = None,
) -> Router:
    """
    Safely configure or update RouterOS API management credentials for a specific router.
    The password is encrypted before saving to the database.
    """
    clean_username = username.strip() if username else ''
    if not clean_username:
        raise ValueError("API username cannot be empty.")

    router.api_username = clean_username
    router.api_password = password

    if api_port is not None:
        if api_port < 1 or api_port > 65535:
            raise ValueError("API port must be between 1 and 65535.")
        router.api_port = api_port

    if use_tls is not None:
        router.use_tls = bool(use_tls)

    router.save(update_fields=['api_username', 'api_password_encrypted', 'api_port', 'use_tls', 'updated_at'])
    return router


def test_router_connection(
    router: Router,
    timeout: float = 4.0,
    client_factory: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """
    Test direct RouterOS API connectivity to a specific router.
    Returns structured diagnostic results with failure taxonomy, latency, and system metadata.
    Does not block or modify router model state in the database.
    """
    start_time = time.perf_counter()

    try:
        if client_factory:
            client = client_factory()
        else:
            client = RouterOSAPIClient.for_router(router, timeout=timeout)

        with client:
            connect_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Query system identity
            identities = client.query('/system/identity/print')
            identity_name = identities[0].get('name') if identities else ''

            # Query system resources
            resources = client.query('/system/resource/print')
            res = resources[0] if resources else {}

            total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            free_mem = int(res.get('free-memory', 0)) if res.get('free-memory') else None
            total_mem = int(res.get('total-memory', 0)) if res.get('total-memory') else None
            cpu_load = int(res.get('cpu-load', 0)) if res.get('cpu-load') is not None else None

            return {
                'success': True,
                'code': 'CONNECTED',
                'message': f"Successfully connected to RouterOS ({router.management_ip}) in {connect_latency_ms}ms.",
                'latency_ms': total_latency_ms,
                'identity': identity_name or router.identity or router.name,
                'routeros_version': res.get('version', router.routeros_version),
                'board_name': res.get('board-name', router.model),
                'model': res.get('board-name', router.model),
                'architecture': res.get('architecture-name', router.architecture),
                'cpu_load': cpu_load,
                'uptime': res.get('uptime'),
                'free_memory_bytes': free_mem,
                'total_memory_bytes': total_mem,
                'details': res,
            }

    except RouterOSError as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning("Router connection test failed for '%s' [%s]: %s", router.name, exc.code, exc.message)
        return {
            'success': False,
            'code': exc.code,
            'message': exc.message,
            'latency_ms': latency_ms,
            'identity': router.identity,
            'routeros_version': router.routeros_version,
            'board_name': router.model,
            'model': router.model,
            'architecture': router.architecture,
            'cpu_load': None,
            'uptime': None,
            'free_memory_bytes': None,
            'total_memory_bytes': None,
            'details': {'error': str(exc), 'code': exc.code},
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error("Unexpected error testing router '%s': %s", router.name, exc)
        return {
            'success': False,
            'code': 'UNKNOWN_ERROR',
            'message': f"Unexpected error connecting to router: {exc}",
            'latency_ms': latency_ms,
            'identity': router.identity,
            'routeros_version': router.routeros_version,
            'board_name': router.model,
            'model': router.model,
            'architecture': router.architecture,
            'cpu_load': None,
            'uptime': None,
            'free_memory_bytes': None,
            'total_memory_bytes': None,
            'details': {'error': str(exc)},
        }


def collect_router_telemetry(
    router: Router,
    timeout: float = 4.0,
    client_factory: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """
    Collect live telemetry and hardware diagnostics from a router.
    Updates cached router health status, system resources, and timestamps in the database.
    Designed for background execution by Celery tasks or explicit manual refresh.
    """
    diag = test_router_connection(router, timeout=timeout, client_factory=client_factory)
    now = timezone.now()

    if diag['success']:
        router.health_status = RouterHealthStatus.ONLINE
        router.health_message = diag['message']
        router.last_seen_at = now
        router.last_health_check_at = now

        if diag.get('identity'):
            router.identity = diag['identity']
        if diag.get('routeros_version'):
            router.routeros_version = diag['routeros_version']
        if diag.get('model'):
            router.model = diag['model']
        if diag.get('architecture'):
            router.architecture = diag['architecture']

        router.system_resources = {
            'cpu_load': diag.get('cpu_load'),
            'uptime': diag.get('uptime'),
            'free_memory_bytes': diag.get('free_memory_bytes'),
            'total_memory_bytes': diag.get('total_memory_bytes'),
            'latency_ms': diag.get('latency_ms'),
            'details': diag.get('details', {}),
            'updated_at': now.isoformat(),
        }

        router.save(update_fields=[
            'health_status',
            'health_message',
            'last_seen_at',
            'last_health_check_at',
            'identity',
            'routeros_version',
            'model',
            'architecture',
            'system_resources',
            'updated_at',
        ])
    else:
        code = diag['code']
        if code == 'ROUTER_CREDENTIALS_NOT_CONFIGURED':
            status = RouterHealthStatus.UNKNOWN
        elif code in ('CONNECTION_TIMEOUT', 'HOST_UNREACHABLE', 'CONNECTION_REFUSED'):
            status = RouterHealthStatus.UNREACHABLE
        elif code in ('AUTHENTICATION_FAILED', 'TLS_ERROR'):
            status = RouterHealthStatus.DEGRADED
        else:
            status = RouterHealthStatus.OFFLINE

        router.health_status = status
        router.health_message = diag['message']
        router.last_health_check_at = now

        resources = dict(router.system_resources or {})
        resources['last_error'] = {
            'code': code,
            'message': diag['message'],
            'failed_at': now.isoformat(),
        }
        router.system_resources = resources

        router.save(update_fields=['health_status', 'health_message', 'last_health_check_at', 'system_resources', 'updated_at'])

    return diag
