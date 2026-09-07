import logging
from typing import Any, Dict

from celery import shared_task

from apps.routers.models import Router
from apps.routers.services.router_service import collect_router_telemetry

logger = logging.getLogger(__name__)


@shared_task(name="poll_router_health_task")
def poll_router_health_task(router_id: str, timeout: float = 4.0) -> Dict[str, Any]:
    """
    Collect live telemetry and update health metrics for a specific router.
    """
    router = Router.objects.filter(id=router_id, is_active=True).first()
    if not router:
        logger.warning("poll_router_health_task called for non-existent or inactive router ID: %s", router_id)
        return {'success': False, 'reason': 'Router not found or inactive'}

    try:
        diag = collect_router_telemetry(router, timeout=timeout)
        logger.info(
            "Router health poll completed for '%s' (%s): status=%s, code=%s",
            router.name,
            router.management_ip,
            router.health_status,
            diag.get('code'),
        )
        return diag
    except Exception as exc:
        logger.error("Error running health poll for router '%s': %s", router.name, exc)
        return {'success': False, 'error': str(exc)}


@shared_task(name="poll_active_routers_task")
def poll_active_routers_task() -> Dict[str, Any]:
    """
    Periodic heartbeat task: iterates through all active routers and triggers telemetry polling.
    """
    active_routers = list(Router.objects.filter(is_active=True).values_list('id', flat=True))
    dispatched = 0

    for r_id in active_routers:
        poll_router_health_task.delay(str(r_id))
        dispatched += 1

    logger.info("Dispatched health poll tasks for %d active router(s).", dispatched)
    return {'dispatched': dispatched, 'total_active': len(active_routers)}
