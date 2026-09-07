from datetime import timedelta
from typing import Any, Optional

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.entitlements.models import AccessEntitlement

from ..models import HotspotSession, SessionStatus


@transaction.atomic
def get_or_create_active_session(
    *,
    company: Company,
    entitlement: AccessEntitlement,
    radius_client: Optional[Any] = None,
    acct_session_id: str,
    username: str,
    mac_address: str,
    ip_address: Optional[str] = None
) -> HotspotSession:
    """
    Idempotently initialize or fetch an active HotspotSession on accounting Start (or missing Start recovery).
    """
    session = HotspotSession.objects.select_for_update().filter(
        company=company,
        acct_session_id=acct_session_id
    ).first()

    if not session:
        session = HotspotSession.objects.create(
            company=company,
            entitlement=entitlement,
            radius_client=radius_client,
            acct_session_id=acct_session_id,
            username=username,
            mac_address=mac_address,
            ip_address=ip_address,
            status=SessionStatus.ACTIVE,
            started_at=timezone.now(),
            last_accounting_at=timezone.now()
        )
        try:
            resolve_session_device_name(session)
        except Exception:
            pass
    else:
        if ip_address and not session.ip_address:
            session.ip_address = ip_address
            session.save(update_fields=['ip_address'])
        if not session.device_name:
            try:
                resolve_session_device_name(session)
            except Exception:
                pass

    return session


def resolve_session_device_name(session: HotspotSession) -> str:
    """
    Resolve and persist the client device name/hostname for a session.
    First checks CustomerDevice, then queries MikroTik DHCP lease table if available.
    """
    if session.device_name:
        return session.device_name

    # 1. CustomerDevice lookup
    dev = None
    try:
        from apps.customers.models import CustomerDevice
        dev = CustomerDevice.objects.filter(
            company=session.company,
            mac_address=session.mac_address
        ).first()
        if dev and dev.device_name:
            session.device_name = dev.device_name
            session.device = dev
            session.save(update_fields=['device_name', 'device', 'updated_at'])
            return dev.device_name
    except Exception:
        pass

    # 2. MikroTik DHCP Leases query
    router = None
    if session.radius_client and getattr(session.radius_client, 'router', None):
        router = session.radius_client.router
    elif session.hotspot and getattr(session.hotspot, 'router', None):
        router = session.hotspot.router
    else:
        from apps.routers.models import Router
        router = Router.objects.filter(company=session.company, is_active=True, api_password_encrypted__gt='').first()

    if router and router.has_credentials:
        try:
            from apps.routers.services.router_client import RouterOSAPIClient
            client = RouterOSAPIClient.for_router(router, timeout=1.5)
            client.connect()
            leases = client.query('/ip/dhcp-server/lease/print', [f'?mac-address={session.mac_address}'])
            if not leases and session.ip_address:
                leases = client.query('/ip/dhcp-server/lease/print', [f'?address={session.ip_address}'])
            if leases:
                hostname = leases[0].get('host-name', '').strip()
                if hostname:
                    session.device_name = hostname
                    session.save(update_fields=['device_name', 'updated_at'])
                    if dev:
                        dev.device_name = hostname
                        dev.save(update_fields=['device_name', 'last_seen_at'])
                    return hostname
        except Exception:
            pass

    return ''


@transaction.atomic
def update_session_accounting(
    *,
    session: HotspotSession,
    input_bytes: int,
    output_bytes: int,
    session_seconds: int,
    ip_address: Optional[str] = None
) -> HotspotSession:
    """
    Update session metrics from cumulative accounting packets safely.
    """
    session.input_bytes = max(session.input_bytes, input_bytes)
    session.output_bytes = max(session.output_bytes, output_bytes)
    session.session_seconds = max(session.session_seconds, session_seconds)
    session.last_accounting_at = timezone.now()
    if ip_address:
        session.ip_address = ip_address

    session.save(update_fields=[
        'input_bytes', 'output_bytes', 'session_seconds', 'last_accounting_at', 'ip_address', 'updated_at'
    ])
    return session


@transaction.atomic
def terminate_session(
    *,
    session: HotspotSession,
    input_bytes: int,
    output_bytes: int,
    session_seconds: int,
    termination_reason: str = ''
) -> HotspotSession:
    """
    Mark session STOPPED upon receiving Accounting Stop.
    """
    session.input_bytes = max(session.input_bytes, input_bytes)
    session.output_bytes = max(session.output_bytes, output_bytes)
    session.session_seconds = max(session.session_seconds, session_seconds)
    session.status = SessionStatus.STOPPED
    session.ended_at = timezone.now()
    session.last_accounting_at = timezone.now()
    session.termination_reason = termination_reason or 'User-Request'

    session.save(update_fields=[
        'input_bytes', 'output_bytes', 'session_seconds', 'status', 'ended_at',
        'last_accounting_at', 'termination_reason', 'updated_at'
    ])
    return session


def get_active_sessions_count_for_entitlement(entitlement: AccessEntitlement) -> int:
    """
    Count valid online active sessions for entitlement simultaneous session limits.
    Filters out stale or unresponsive sessions beyond the grace threshold.
    """
    stale_cutoff = timezone.now() - timedelta(seconds=getattr(settings, 'RADIUS_SESSION_STALE_AFTER_SECONDS', 300))
    return HotspotSession.objects.filter(
        entitlement=entitlement,
        status=SessionStatus.ACTIVE
    ).filter(
        models.Q(last_accounting_at__gte=stale_cutoff) |
        models.Q(last_accounting_at__isnull=True, started_at__gte=stale_cutoff)
    ).count()
