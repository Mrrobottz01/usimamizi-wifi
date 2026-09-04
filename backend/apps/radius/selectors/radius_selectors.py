from typing import Optional

from .models import RadiusAccountingLog, RadiusClient


def get_radius_client_by_ip(nas_ip: str) -> Optional[RadiusClient]:
    """
    Lookup active RADIUS NAS client by IP address.
    """
    try:
        return RadiusClient.objects.get(nas_ip=nas_ip, is_active=True)
    except RadiusClient.DoesNotExist:
        return None


def get_latest_accounting_log_for_session(session_id: str) -> Optional[RadiusAccountingLog]:
    """
    Retrieve latest accounting packet logged for a session ID.
    """
    return RadiusAccountingLog.objects.filter(session_id=session_id).order_by('-created_at').first()
