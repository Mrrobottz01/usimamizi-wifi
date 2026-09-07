import logging
from typing import Any, Dict, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.locations.models import Location, LocationStatus
from apps.routers.models import Router, RouterHealthStatus
from apps.hotspot_sessions.models import HotspotSession, SessionStatus

logger = logging.getLogger(__name__)


def calculate_location_network_health(location: Location) -> Tuple[str, Dict[str, Any]]:
    """
    Derives operational network health for a location based purely on cached router telemetry.
    Zero live RouterOS calls are made.

    Rules:
    - HEALTHY: active routers exist and all are ONLINE
    - DEGRADED: at least one active router is ONLINE, but some are DEGRADED/UNREACHABLE/OFFLINE
    - OFFLINE: active routers exist, but zero are ONLINE
    - UNKNOWN: no routers deployed or no health evidence recorded
    """
    active_routers = list(location.routers.filter(is_active=True))
    router_count = len(active_routers)

    summary: Dict[str, Any] = {
        'router_count': router_count,
        'online_router_count': 0,
        'degraded_router_count': 0,
        'unreachable_router_count': 0,
        'unknown_router_count': 0,
        'last_network_update_at': None,
    }

    if router_count == 0:
        return 'UNKNOWN', summary

    timestamps = []
    for r in active_routers:
        if r.health_status == RouterHealthStatus.ONLINE:
            summary['online_router_count'] += 1
        elif r.health_status == RouterHealthStatus.DEGRADED:
            summary['degraded_router_count'] += 1
        elif r.health_status in (RouterHealthStatus.UNREACHABLE, RouterHealthStatus.OFFLINE):
            summary['unreachable_router_count'] += 1
        else:
            summary['unknown_router_count'] += 1

        if r.last_health_check_at:
            timestamps.append(r.last_health_check_at)
        elif r.last_seen_at:
            timestamps.append(r.last_seen_at)

    if timestamps:
        summary['last_network_update_at'] = max(timestamps).isoformat()

    online = summary['online_router_count']
    if online == router_count:
        health = 'HEALTHY'
    elif online > 0:
        health = 'DEGRADED'
    elif (summary['degraded_router_count'] > 0 or summary['unreachable_router_count'] > 0):
        health = 'OFFLINE'
    else:
        health = 'UNKNOWN'

    return health, summary


@transaction.atomic
def move_router_to_location(
    *,
    router: Router,
    new_location: Location,
    user=None
) -> Router:
    """
    Relocate a Router to a new Location within the same tenant company.
    Synchronously updates currently hosted HotSpot configurations to match
    the new hosting location, preserving structured integrity.
    Historical payment and session snapshots remain unaltered.
    """
    if router.company_id != new_location.company_id:
        raise ValidationError({
            'location': f"Target location '{new_location.name}' belongs to a different company."
        })

    old_location_id = router.location_id
    if old_location_id == new_location.id:
        return router

    # 1. Update router location
    router.location = new_location
    router.save(update_fields=['location', 'updated_at'])

    # 2. Update hosted hotspots location for consistency
    updated_hotspots = router.hotspots.all()
    updated_hotspots_count = updated_hotspots.count()
    router.hotspots.update(location=new_location)

    # 3. Create audit trail
    AuditLog.objects.create(
        company=router.company,
        user=user,
        action='ROUTER_MOVED_LOCATION',
        resource_type='Router',
        resource_id=str(router.id),
        changes={
            'router_name': router.name,
            'from_location_id': str(old_location_id),
            'to_location_id': str(new_location.id),
            'to_location_name': new_location.name,
            'hotspots_reassigned': updated_hotspots_count,
        }
    )

    logger.info(
        f"Router '{router.name}' ({router.id}) moved from Location {old_location_id} to {new_location.id} by {user}."
    )
    return router


@transaction.atomic
def deactivate_location(*, location: Location, user=None) -> Location:
    """
    Deactivate and archive a location. Does not disable routers or disconnect customers.
    """
    location.is_active = False
    location.status = LocationStatus.INACTIVE
    location.save(update_fields=['is_active', 'status', 'updated_at'])

    AuditLog.objects.create(
        company=location.company,
        user=user,
        action='LOCATION_DEACTIVATED',
        resource_type='Location',
        resource_id=str(location.id),
        changes={'status': LocationStatus.INACTIVE, 'is_active': False}
    )
    return location


@transaction.atomic
def reactivate_location(*, location: Location, user=None) -> Location:
    """
    Reactivate a previously deactivated location.
    """
    location.is_active = True
    location.status = LocationStatus.ACTIVE
    location.save(update_fields=['is_active', 'status', 'updated_at'])

    AuditLog.objects.create(
        company=location.company,
        user=user,
        action='LOCATION_REACTIVATED',
        resource_type='Location',
        resource_id=str(location.id),
        changes={'status': LocationStatus.ACTIVE, 'is_active': True}
    )
    return location


@transaction.atomic
def safe_delete_location(*, location: Location, user=None) -> Tuple[str, str]:
    """
    Safely delete or deactivate a location.
    - If referenced by routers, hotspots, or active sessions: deactivates rather than hard delete.
    - If unreferenced: deletes permanently.
    """
    has_routers = location.routers.exists()
    has_hotspots = location.hotspots.exists()
    has_sessions = HotspotSession.objects.filter(hotspot__location=location).exists()

    if has_routers or has_hotspots or has_sessions:
        deactivate_location(location=location, user=user)
        return 'deactivated', (
            f"Location '{location.name}' has active infrastructure "
            f"({location.routers.count()} router(s), {location.hotspots.count()} hotspot(s)) "
            "and was deactivated rather than deleted."
        )

    loc_name = location.name
    loc_id = str(location.id)
    comp = location.company
    location.delete()

    AuditLog.objects.create(
        company=comp,
        user=user,
        action='LOCATION_DELETED',
        resource_type='Location',
        resource_id=loc_id,
        changes={'name': loc_name}
    )
    return 'deleted', f"Location '{loc_name}' deleted."