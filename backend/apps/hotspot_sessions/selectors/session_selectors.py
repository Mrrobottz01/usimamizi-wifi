from typing import Any, Dict

from django.db.models import Count, Q, QuerySet

from apps.companies.models import Company

from ..models import HotspotSession, SessionStatus


def get_sessions_queryset(company: Company, filters: Dict[str, Any]) -> QuerySet:
    """
    Retrieve optimized QuerySet of hotspot sessions.
    """
    qs = HotspotSession.objects.filter(company=company)

    status = filters.get('status')
    if status:
        qs = qs.filter(status=status)

    entitlement_id = filters.get('entitlement_id')
    if entitlement_id:
        qs = qs.filter(entitlement_id=entitlement_id)

    mac_address = filters.get('mac_address')
    if mac_address:
        qs = qs.filter(mac_address__iexact=mac_address)

    search = filters.get('search')
    if search:
        search = search.strip()
        qs = qs.filter(
            Q(username__icontains=search) |
            Q(mac_address__icontains=search) |
            Q(ip_address__icontains=search) |
            Q(entitlement__reference__icontains=search) |
            Q(acct_session_id__icontains=search)
        )

    sort_by = filters.get('sort_by', '-started_at')
    allowed_sorts = ['started_at', '-started_at', 'session_seconds', '-session_seconds', 'input_bytes', 'output_bytes']
    if sort_by in allowed_sorts:
        qs = qs.order_by(sort_by)
    else:
        qs = qs.order_by('-started_at')

    return qs.select_related('entitlement', 'entitlement__plan', 'radius_client').distinct()


def calculate_session_summary_metrics(company: Company, queryset: QuerySet = None) -> Dict[str, Any]:
    """
    Calculate summary stats for hotspot sessions.
    """
    if queryset is None:
        queryset = HotspotSession.objects.filter(company=company)

    total = queryset.count()
    counts = queryset.values('status').annotate(count=Count('id'))
    status_map = {c['status']: c['count'] for c in counts}

    return {
        "total_sessions": total,
        "active": status_map.get(SessionStatus.ACTIVE, 0),
        "stopped": status_map.get(SessionStatus.STOPPED, 0),
        "stale": status_map.get(SessionStatus.STALE, 0),
    }
