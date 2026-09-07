import hashlib
import logging
import os
import socket
import struct
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union

from django.db import connection
from django.utils import timezone

from apps.companies.models import Company
from apps.core.models import IncidentStatus, ServiceIncident, ServiceName, SystemWatchdogConfig
from apps.notifications.models import NotificationMessage, NotificationStatus
from apps.notifications.services.sms_services import normalize_phone_number, route_and_send_sms
from apps.routers.models import Router, RouterHealthStatus

logger = logging.getLogger(__name__)


@dataclass
class ProbeResult:
    """
    Standardized result data structure from a service health probe.
    """
    service_name: str
    service_identifier: str
    status: str  # IncidentStatus: HEALTHY, DOWN, DEGRADED
    is_healthy: bool
    latency_ms: float = 0.0
    error_message: str = ''
    extra_data: Dict[str, Any] = field(default_factory=dict)


def _build_radius_probe_packet(secret: str = 'testing123') -> bytes:
    """
    Constructs a valid RFC 2865 RADIUS Access-Request packet with User-Name='watchdog-probe'.
    """
    code = 1  # Access-Request
    identifier = 0x5A
    req_authenticator = os.urandom(16)
    
    # Attribute 1: User-Name
    username = b"watchdog-probe"
    attr_user = bytes([1, 2 + len(username)]) + username
    
    # Attribute 32: NAS-Identifier
    nas_id = b"UsimamiziWatchdog"
    attr_nas = bytes([32, 2 + len(nas_id)]) + nas_id
    
    attributes = attr_user + attr_nas
    length = 20 + len(attributes)
    
    header = struct.pack("!BBH", code, identifier, length) + req_authenticator
    return header + attributes


def probe_freeradius(
    host: str = '127.0.0.1',
    port: int = 1812,
    secret: str = 'testing123',
    timeout: float = 1.0
) -> ProbeResult:
    """
    Probes FreeRADIUS authentication service by sending an Access-Request over UDP socket.
    Any response (Access-Accept, Access-Reject, Access-Challenge) confirms the daemon is active.
    """
    service_id = f"{host}:{port}"
    start_time = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    try:
        packet = _build_radius_probe_packet(secret=secret)
        sock.sendto(packet, (host, port))
        
        data, server = sock.recvfrom(1024)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        if len(data) >= 20:
            code = data[0]
            # 2=Access-Accept, 3=Access-Reject, 11=Access-Challenge
            radius_responses = {1: 'Access-Request', 2: 'Access-Accept', 3: 'Access-Reject', 11: 'Access-Challenge'}
            response_name = radius_responses.get(code, f"Code-{code}")
            
            return ProbeResult(
                service_name=ServiceName.FREERADIUS,
                service_identifier=service_id,
                status=IncidentStatus.HEALTHY,
                is_healthy=True,
                latency_ms=elapsed_ms,
                extra_data={'response_code': code, 'response_type': response_name}
            )
        else:
            return ProbeResult(
                service_name=ServiceName.FREERADIUS,
                service_identifier=service_id,
                status=IncidentStatus.DEGRADED,
                is_healthy=False,
                latency_ms=elapsed_ms,
                error_message=f"Received truncated packet ({len(data)} bytes) from RADIUS server."
            )

    except socket.timeout:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ProbeResult(
            service_name=ServiceName.FREERADIUS,
            service_identifier=service_id,
            status=IncidentStatus.DOWN,
            is_healthy=False,
            latency_ms=elapsed_ms,
            error_message=f"FreeRADIUS at {service_id} timed out after {timeout}s (no response to UDP authentication probe)."
        )
    except ConnectionRefusedError:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ProbeResult(
            service_name=ServiceName.FREERADIUS,
            service_identifier=service_id,
            status=IncidentStatus.DOWN,
            is_healthy=False,
            latency_ms=elapsed_ms,
            error_message=f"Connection refused on {service_id} (FreeRADIUS daemon is not running)."
        )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ProbeResult(
            service_name=ServiceName.FREERADIUS,
            service_identifier=service_id,
            status=IncidentStatus.DOWN,
            is_healthy=False,
            latency_ms=elapsed_ms,
            error_message=f"RADIUS probe error on {service_id}: {str(exc)}"
        )
    finally:
        sock.close()


def probe_database(timeout: float = 3.0) -> ProbeResult:
    """
    Probes primary SQL database connection and measures query round-trip latency.
    """
    start_time = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ProbeResult(
            service_name=ServiceName.DATABASE,
            service_identifier=str(connection.settings_dict.get('NAME', 'default_db')),
            status=IncidentStatus.HEALTHY,
            is_healthy=True,
            latency_ms=elapsed_ms
        )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ProbeResult(
            service_name=ServiceName.DATABASE,
            service_identifier=str(connection.settings_dict.get('NAME', 'default_db')),
            status=IncidentStatus.DOWN,
            is_healthy=False,
            latency_ms=elapsed_ms,
            error_message=f"Database probe failed: {str(exc)}"
        )


def probe_router(router: Router, timeout: float = 3.0) -> ProbeResult:
    """
    Probes router network reachability and RouterOS API port (default: 8728).
    Updates router health_status and telemetry fields.
    """
    service_id = f"{router.management_ip}:{router.api_port}"
    start_time = time.perf_counter()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        sock.connect((router.management_ip, router.api_port))
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Mark router online
        router.health_status = RouterHealthStatus.ONLINE
        router.last_seen_at = timezone.now()
        router.last_health_check_at = timezone.now()
        router.health_message = f"Reachable via API port {router.api_port} ({elapsed_ms}ms)"
        router.save(update_fields=['health_status', 'last_seen_at', 'last_health_check_at', 'health_message'])
        
        return ProbeResult(
            service_name=ServiceName.ROUTER_GATEWAY,
            service_identifier=f"{router.name} ({service_id})",
            status=IncidentStatus.HEALTHY,
            is_healthy=True,
            latency_ms=elapsed_ms,
            extra_data={'router_id': str(router.id), 'router_name': router.name}
        )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        router.health_status = RouterHealthStatus.OFFLINE
        router.last_health_check_at = timezone.now()
        router.health_message = f"Unreachable: {str(exc)}"
        router.save(update_fields=['health_status', 'last_health_check_at', 'health_message'])
        
        return ProbeResult(
            service_name=ServiceName.ROUTER_GATEWAY,
            service_identifier=f"{router.name} ({service_id})",
            status=IncidentStatus.DOWN,
            is_healthy=False,
            latency_ms=elapsed_ms,
            error_message=f"Router {router.name} ({service_id}) unreachable: {str(exc)}",
            extra_data={'router_id': str(router.id), 'router_name': router.name}
        )
    finally:
        sock.close()


def send_system_alert_sms(
    *,
    phone_numbers: Union[str, List[str]],
    alert_title: str,
    alert_message: str,
    company: Optional[Company] = None
) -> List[NotificationMessage]:
    """
    Dispatches instant outage or recovery SMS alert to designated administrator phones.
    """
    if isinstance(phone_numbers, str):
        numbers = [n.strip() for n in phone_numbers.split(',') if n.strip()]
    else:
        numbers = [str(n).strip() for n in phone_numbers if str(n).strip()]

    if not numbers:
        logger.warning("No phone numbers configured for system alert SMS.")
        return []

    # Resolve company context for notification billing/config
    target_company = company or Company.objects.first()
    if not target_company:
        logger.warning("No company available in system to send notification SMS.")
        return []

    now_str = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
    body = (
        f"USIMAMIZI ALERT: {alert_title}\n"
        f"{alert_message}\n"
        f"Time: {now_str}"
    )

    results = []
    for raw_phone in numbers:
        phone_norm = normalize_phone_number(raw_phone)
        if not phone_norm:
            continue

        notification_msg = NotificationMessage.objects.create(
            company=target_company,
            channel='SMS',
            recipient=raw_phone,
            phone_normalized=phone_norm,
            rendered_content=body,
            status=NotificationStatus.QUEUED
        )

        try:
            route_and_send_sms(notification_message=notification_msg)
        except Exception as exc:
            logger.exception("Failed to dispatch alert SMS to %s: %s", phone_norm, exc)

        results.append(notification_msg)

    return results


def evaluate_and_alert_service(
    probe_result: ProbeResult,
    config: Optional[SystemWatchdogConfig] = None,
    company: Optional[Company] = None,
    send_alerts: bool = True
) -> Optional[ServiceIncident]:
    """
    Manages the lifecycle of a ServiceIncident:
    1. If service is DOWN: creates incident, sends SMS alert, or applies cooldown.
    2. If service is HEALTHY and was DOWN: marks resolved, sends recovery SMS alert.
    """
    if config is None:
        config = SystemWatchdogConfig.objects.filter(company=company, is_enabled=True).first()
        if not config:
            config = SystemWatchdogConfig.objects.filter(company__isnull=True, is_enabled=True).first()
        if not config:
            config = SystemWatchdogConfig.objects.create(company=company, is_enabled=True)

    if not config.is_enabled:
        return None

    # Search for any currently open incident for this exact service and identifier
    active_incident = ServiceIncident.objects.filter(
        company=company,
        service_name=probe_result.service_name,
        service_identifier=probe_result.service_identifier,
        resolved_at__isnull=True
    ).order_by('-detected_at').first()

    now = timezone.now()

    if not probe_result.is_healthy:
        if not active_incident:
            # New incident detected!
            active_incident = ServiceIncident.objects.create(
                company=company,
                service_name=probe_result.service_name,
                service_identifier=probe_result.service_identifier,
                status=probe_result.status,
                error_message=probe_result.error_message,
                detected_at=now
            )

            if send_alerts and config.alert_phone_numbers:
                alert_title = f"{probe_result.service_name} OUTAGE DETECTED"
                alert_msg = f"Service '{probe_result.service_name}' ({probe_result.service_identifier}) is DOWN.\nReason: {probe_result.error_message}"
                send_system_alert_sms(
                    phone_numbers=config.alert_phone_numbers,
                    alert_title=alert_title,
                    alert_message=alert_msg,
                    company=company
                )
                active_incident.alert_sent_at = now
                active_incident.alert_count = 1
                active_incident.save(update_fields=['alert_sent_at', 'alert_count'])
                logger.error("[WATCHDOG ALERT] Initial SMS alert dispatched for %s (%s)", probe_result.service_name, probe_result.service_identifier)

        else:
            # Active incident already ongoing
            active_incident.error_message = probe_result.error_message
            active_incident.status = probe_result.status

            # Check alert cooldown to avoid burning operator SMS balance
            cooldown_seconds = config.alert_cooldown_minutes * 60
            time_since_alert = (now - active_incident.alert_sent_at).total_seconds() if active_incident.alert_sent_at else float('inf')

            if time_since_alert >= cooldown_seconds and send_alerts and config.alert_phone_numbers:
                alert_title = f"{probe_result.service_name} STILL DOWN (Cooldown Expired)"
                alert_msg = f"Persistent outage for '{probe_result.service_name}' ({probe_result.service_identifier}). Ongoing for {int((now - active_incident.detected_at).total_seconds() // 60)} min."
                send_system_alert_sms(
                    phone_numbers=config.alert_phone_numbers,
                    alert_title=alert_title,
                    alert_message=alert_msg,
                    company=company
                )
                active_incident.alert_sent_at = now
                active_incident.alert_count += 1
                logger.warning("[WATCHDOG ALERT] Repeat SMS alert dispatched after cooldown for %s", probe_result.service_name)

            active_incident.save(update_fields=['error_message', 'status', 'alert_sent_at', 'alert_count'])

        return active_incident

    else:
        # Service is currently HEALTHY
        if active_incident:
            # Service has recovered!
            active_incident.resolved_at = now
            active_incident.status = IncidentStatus.HEALTHY
            active_incident.save(update_fields=['resolved_at', 'status'])

            downtime_minutes = max(1, int((now - active_incident.detected_at).total_seconds() // 60))

            if config.notify_on_recovery and active_incident.alert_count > 0 and send_alerts and config.alert_phone_numbers:
                recovery_title = f"{probe_result.service_name} RECOVERED"
                recovery_msg = f"Service '{probe_result.service_name}' ({probe_result.service_identifier}) is back ONLINE. Total downtime was ~{downtime_minutes} min."
                send_system_alert_sms(
                    phone_numbers=config.alert_phone_numbers,
                    alert_title=recovery_title,
                    alert_message=recovery_msg,
                    company=company
                )
                active_incident.recovery_alert_sent_at = now
                active_incident.save(update_fields=['recovery_alert_sent_at'])
                logger.info("[WATCHDOG RESOLVED] Recovery SMS alert dispatched for %s", probe_result.service_name)

            return active_incident

        return None


def run_full_watchdog_cycle(
    company: Optional[Company] = None,
    send_alerts: bool = True
) -> Dict[str, Any]:
    """
    Executes a complete health check cycle across FreeRADIUS, Active Routers, and Database.
    Evaluates incidents and dispatches alerts accordingly.
    """
    config = SystemWatchdogConfig.objects.filter(company=company, is_enabled=True).first()
    if not config:
        config = SystemWatchdogConfig.objects.filter(company__isnull=True, is_enabled=True).first()
    if not config:
        config = SystemWatchdogConfig.objects.create(company=company, is_enabled=True)

    results = []

    # 1. Probe FreeRADIUS
    radius_probe = probe_freeradius(
        host=config.radius_host,
        port=config.radius_auth_port,
        secret=config.radius_secret
    )
    evaluate_and_alert_service(radius_probe, config=config, company=company, send_alerts=send_alerts)
    results.append(radius_probe)

    # 2. Probe Database
    db_probe = probe_database()
    evaluate_and_alert_service(db_probe, config=config, company=company, send_alerts=send_alerts)
    results.append(db_probe)

    # 3. Probe Active Routers
    router_qs = Router.objects.filter(is_active=True)
    if company:
        router_qs = router_qs.filter(company=company)

    for router in router_qs:
        r_probe = probe_router(router)
        evaluate_and_alert_service(r_probe, config=config, company=company, send_alerts=send_alerts)
        results.append(r_probe)

    overall_healthy = all(r.is_healthy for r in results)

    return {
        'timestamp': timezone.now().isoformat(),
        'overall_status': 'HEALTHY' if overall_healthy else 'DEGRADED',
        'probes': [
            {
                'service_name': r.service_name,
                'service_identifier': r.service_identifier,
                'status': r.status,
                'is_healthy': r.is_healthy,
                'latency_ms': r.latency_ms,
                'error_message': r.error_message,
                'extra_data': r.extra_data,
            }
            for r in results
        ]
    }
