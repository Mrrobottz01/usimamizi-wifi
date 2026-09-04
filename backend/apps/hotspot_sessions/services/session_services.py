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
    else:
        if ip_address and not session.ip_address:
            session.ip_address = ip_address
            session.save(update_fields=['ip_address'])

    return session


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
