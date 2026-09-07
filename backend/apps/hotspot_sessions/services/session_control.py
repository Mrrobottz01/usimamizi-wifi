import hashlib
import logging
import random
import socket
import struct
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.companies.models import Company
from apps.entitlements.models import AccessEntitlement
from apps.hotspot_sessions.models import (
    DisconnectStatus,
    HotspotSession,
    SessionDisconnectRequest,
    SessionDisconnectTrigger,
    SessionStatus,
)
from apps.radius.models import EntitlementDevice, RadiusClient
from apps.radius.services.radius_services import normalize_mac_address

logger = logging.getLogger(__name__)

# RFC 3576 / RFC 5176 RADIUS Dynamic Authorization Codes
RADIUS_CODE_DISCONNECT_REQUEST = 40
RADIUS_CODE_DISCONNECT_ACK = 41
RADIUS_CODE_DISCONNECT_NAK = 42

# Standard RADIUS Attribute Types
RADIUS_ATTR_USER_NAME = 1
RADIUS_ATTR_NAS_IP_ADDRESS = 4
RADIUS_ATTR_FRAMED_IP_ADDRESS = 8
RADIUS_ATTR_CALLING_STATION_ID = 31
RADIUS_ATTR_ACCT_SESSION_ID = 44
RADIUS_ATTR_ERROR_CAUSE = 101


def _encode_radius_attribute(attr_type: int, value: Any) -> bytes:
    """Encode a RADIUS attribute into Type-Length-Value (TLV) binary format."""
    if isinstance(value, str):
        val_bytes = value.encode('utf-8')
    elif isinstance(value, bytes):
        val_bytes = value
    elif isinstance(value, int):
        val_bytes = struct.pack('!I', value)
    elif isinstance(value, socket.inet_aton.__class__):
        val_bytes = value
    else:
        val_bytes = str(value).encode('utf-8')

    length = len(val_bytes) + 2
    return struct.pack('!BB', attr_type, length) + val_bytes


def build_disconnect_packet(
    *,
    identifier: int,
    secret: str,
    username: str,
    acct_session_id: str,
    nas_ip: Optional[str] = None,
    framed_ip: Optional[str] = None,
    calling_station_id: Optional[str] = None,
) -> Tuple[bytes, bytes]:
    """
    Build RFC 3576 Disconnect-Request packet with Request Authenticator.
    Returns (packet_bytes, request_authenticator).
    """
    attrs = bytearray()
    if username:
        attrs.extend(_encode_radius_attribute(RADIUS_ATTR_USER_NAME, username))
    if acct_session_id:
        attrs.extend(_encode_radius_attribute(RADIUS_ATTR_ACCT_SESSION_ID, acct_session_id))
    if calling_station_id:
        attrs.extend(_encode_radius_attribute(RADIUS_ATTR_CALLING_STATION_ID, calling_station_id))
    if nas_ip:
        try:
            attrs.extend(_encode_radius_attribute(RADIUS_ATTR_NAS_IP_ADDRESS, socket.inet_aton(nas_ip)))
        except (socket.error, OSError):
            pass
    if framed_ip:
        try:
            attrs.extend(_encode_radius_attribute(RADIUS_ATTR_FRAMED_IP_ADDRESS, socket.inet_aton(framed_ip)))
        except (socket.error, OSError):
            pass

    # Header: Code (1), Identifier (1), Length (2), Authenticator (16)
    total_length = 20 + len(attrs)
    zero_auth = b'\x00' * 16

    # Calculate Request Authenticator: MD5(Code + ID + Length + 16 zero octets + Attributes + Secret)
    header_for_hash = struct.pack('!BBH', RADIUS_CODE_DISCONNECT_REQUEST, identifier, total_length) + zero_auth + bytes(attrs) + secret.encode('utf-8')
    request_authenticator = hashlib.md5(header_for_hash).digest()

    packet = struct.pack('!BBH', RADIUS_CODE_DISCONNECT_REQUEST, identifier, total_length) + request_authenticator + bytes(attrs)
    return packet, request_authenticator


def send_radius_disconnect_packet(
    *,
    nas_ip: str,
    secret: str,
    username: str,
    acct_session_id: str,
    calling_station_id: Optional[str] = None,
    framed_ip: Optional[str] = None,
    coa_port: int = 3799,
    timeout_seconds: Optional[float] = None,
    max_retries: int = 2
) -> Dict[str, Any]:
    """
    Send RFC 3576 Disconnect-Request over UDP to MikroTik NAS on UDP 3799.
    Returns dictionary with status code, response code, and messages.
    """
    timeout = timeout_seconds or getattr(settings, 'RADIUS_DISCONNECT_TIMEOUT_SECONDS', 3.0)
    identifier = random.randint(1, 255)

    packet_bytes, req_auth = build_disconnect_packet(
        identifier=identifier,
        secret=secret,
        username=username,
        acct_session_id=acct_session_id,
        nas_ip=nas_ip,
        framed_ip=framed_ip,
        calling_station_id=calling_station_id,
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    attempt = 0
    last_err = ""

    try:
        while attempt < max_retries:
            attempt += 1
            try:
                sock.sendto(packet_bytes, (nas_ip, coa_port))
                resp_data, server_addr = sock.recvfrom(4096)

                if len(resp_data) < 20:
                    last_err = "Malformed short RADIUS response"
                    continue

                resp_code, resp_id, resp_len = struct.unpack('!BBH', resp_data[:4])
                resp_auth = resp_data[4:20]
                resp_attrs = resp_data[20:resp_len]

                # Verify Response Authenticator: MD5(Code + ID + Length + RequestAuth + Attributes + Secret)
                expected_hash = hashlib.md5(
                    struct.pack('!BBH', resp_code, resp_id, resp_len) +
                    req_auth +
                    resp_attrs +
                    secret.encode('utf-8')
                ).digest()

                if resp_auth != expected_hash:
                    logger.warning("RADIUS Response Authenticator verification failed from %s", nas_ip)

                if resp_code == RADIUS_CODE_DISCONNECT_ACK:
                    return {
                        "success": True,
                        "status": DisconnectStatus.ACKNOWLEDGED,
                        "response_code": "Disconnect-ACK",
                        "response_message": f"Successfully acknowledged by NAS {nas_ip}",
                        "attempts": attempt
                    }
                elif resp_code == RADIUS_CODE_DISCONNECT_NAK:
                    return {
                        "success": False,
                        "status": DisconnectStatus.FAILED,
                        "response_code": "Disconnect-NAK",
                        "response_message": f"Rejected by NAS {nas_ip} (Disconnect-NAK)",
                        "attempts": attempt,
                        "last_error": "NAS rejected disconnect request"
                    }
                else:
                    return {
                        "success": False,
                        "status": DisconnectStatus.FAILED,
                        "response_code": f"Unknown Code ({resp_code})",
                        "response_message": f"Unexpected RADIUS code {resp_code}",
                        "attempts": attempt,
                        "last_error": f"Unexpected code {resp_code}"
                    }

            except socket.timeout:
                last_err = f"Timeout waiting for response from {nas_ip}:{coa_port}"
                logger.info("RADIUS Disconnect-Request attempt %d timed out to %s", attempt, nas_ip)
            except Exception as e:
                last_err = str(e)
                logger.error("Socket error sending Disconnect-Request to %s: %s", nas_ip, e)

        return {
            "success": False,
            "status": DisconnectStatus.TIMEOUT,
            "response_code": "TIMEOUT",
            "response_message": last_err,
            "attempts": attempt,
            "last_error": last_err
        }

    finally:
        sock.close()


@transaction.atomic
def disconnect_hotspot_session(
    *,
    session: HotspotSession,
    trigger_type: str = SessionDisconnectTrigger.MANUAL,
    reason: str = '',
    requested_by=None
) -> SessionDisconnectRequest:
    """
    Initiate and record a RADIUS Disconnect-Request for an active HotspotSession.
    """
    if session.status != SessionStatus.ACTIVE:
        # If already stopped or stale, return existing or completed record
        existing = session.disconnect_requests.first()
        if existing:
            return existing
        req = SessionDisconnectRequest.objects.create(
            company=session.company,
            hotspot_session=session,
            radius_client=session.radius_client,
            trigger_type=trigger_type,
            status=DisconnectStatus.CANCELLED,
            reason=reason or f"Session already {session.status}",
            requested_by=requested_by,
            response_code=f"ALREADY_{session.status}"
        )
        return req

    # Idempotency check: reuse in-flight pending/sending request
    in_flight = session.disconnect_requests.filter(
        status__in=[DisconnectStatus.PENDING, DisconnectStatus.SENDING]
    ).first()
    if in_flight:
        return in_flight

    # Resolve NAS RadiusClient
    nas = session.radius_client
    if not nas and hasattr(session, 'hotspot') and session.hotspot and session.hotspot.router:
        nas = session.hotspot.router.radius_clients.filter(is_active=True).first()
    if not nas:
        nas = RadiusClient.objects.filter(company=session.company, is_active=True).first()

    disconnect_req = SessionDisconnectRequest.objects.create(
        company=session.company,
        hotspot_session=session,
        radius_client=nas,
        trigger_type=trigger_type,
        status=DisconnectStatus.SENDING,
        reason=reason,
        requested_by=requested_by,
        sent_at=timezone.now(),
        attempt_count=1
    )

    if not nas or not nas.is_active:
        disconnect_req.status = DisconnectStatus.FAILED
        disconnect_req.failed_at = timezone.now()
        disconnect_req.last_error = "No active NAS configured for session"
        disconnect_req.save()
        return disconnect_req

    nas_ip = nas.nas_ip
    secret = nas.shared_secret or "radius_shared_secret_lab"

    # Send dynamic authorization UDP packet
    net_result = send_radius_disconnect_packet(
        nas_ip=nas_ip,
        secret=secret,
        username=session.username,
        acct_session_id=session.acct_session_id,
        calling_station_id=session.mac_address,
        framed_ip=session.ip_address,
    )

    disconnect_req.status = net_result["status"]
    disconnect_req.attempt_count = net_result["attempts"]
    disconnect_req.response_code = net_result.get("response_code", "")
    disconnect_req.response_message = net_result.get("response_message", "")
    disconnect_req.last_error = net_result.get("last_error", "")

    if net_result["success"]:
        disconnect_req.acknowledged_at = timezone.now()
    else:
        disconnect_req.failed_at = timezone.now()

    disconnect_req.save()

    # Log to AuditLog
    AuditLog.objects.create(
        company=session.company,
        user=requested_by,
        action="SESSION_DISCONNECT_REQUESTED",
        resource_type="HotspotSession",
        resource_id=str(session.id),
        changes={
            "trigger_type": trigger_type,
            "status": disconnect_req.status,
            "nas_ip": nas_ip,
            "username": session.username,
            "mac_address": session.mac_address,
            "reason": reason
        }
    )

    return disconnect_req


def disconnect_active_sessions_for_entitlement(
    *,
    entitlement: AccessEntitlement,
    trigger_type: str,
    reason: str = '',
    requested_by=None
) -> List[SessionDisconnectRequest]:
    """
    Disconnect all active physical sessions attached to an AccessEntitlement.
    """
    active_sessions = HotspotSession.objects.filter(
        entitlement=entitlement,
        status=SessionStatus.ACTIVE
    )
    requests = []
    for sess in active_sessions:
        req = disconnect_hotspot_session(
            session=sess,
            trigger_type=trigger_type,
            reason=reason,
            requested_by=requested_by
        )
        requests.append(req)
    return requests


def reconcile_stale_sessions(
    *,
    company: Optional[Company] = None,
    stale_threshold_seconds: Optional[int] = None
) -> int:
    """
    Identify and transition unresponsive ACTIVE sessions to STALE.
    """
    threshold_sec = stale_threshold_seconds or getattr(settings, 'RADIUS_SESSION_STALE_AFTER_SECONDS', 300)
    cutoff = timezone.now() - timedelta(seconds=threshold_sec)

    qs = HotspotSession.objects.filter(status=SessionStatus.ACTIVE)
    if company:
        qs = qs.filter(company=company)

    # Sessions where last accounting was before cutoff, or never received accounting and started before cutoff
    stale_candidates = qs.filter(
        models.Q(last_accounting_at__lt=cutoff) |
        models.Q(last_accounting_at__isnull=True, started_at__lt=cutoff)
    )

    count = 0
    for sess in stale_candidates:
        sess.status = SessionStatus.STALE
        sess.termination_reason = "STALE_ACCOUNTING_TIMEOUT"
        sess.save(update_fields=['status', 'termination_reason', 'updated_at'])
        count += 1

    return count


@transaction.atomic
def release_entitlement_device(
    *,
    entitlement: AccessEntitlement,
    mac_address: str,
    company: Company,
    user=None,
    reason: str = ''
) -> bool:
    """
    Release a bound client MAC address from an AccessEntitlement to permit device replacement.
    """
    if entitlement.company_id != company.id:
        raise ValidationError({'entitlement': 'Entitlement does not belong to company.'})

    norm_mac = normalize_mac_address(mac_address)
    device = EntitlementDevice.objects.filter(
        entitlement=entitlement,
        mac_address=norm_mac
    ).first()

    if not device:
        return False

    device.delete()

    AuditLog.objects.create(
        company=company,
        user=user,
        action="ENTITLEMENT_DEVICE_RELEASED",
        resource_type="AccessEntitlement",
        resource_id=str(entitlement.id),
        changes={
            "mac_address": norm_mac,
            "reason": reason
        }
    )

    return True
