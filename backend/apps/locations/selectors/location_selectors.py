from typing import Any, Dict, Optional
from django.db.models import Count, Q, QuerySet
from apps.companies.models import Company
from apps.locations.models import Location
from apps.routers.models import RouterHealthStatus
from apps.hotspot_sessions.models import SessionStatus


def get_location_by_id(location_id: Any, company: Optional[Company] = None) -> Optional[Location]:
    """
    Retrieve single location by UUID, enforcing company scoping if provided.
    """
    qs = Location.objects.select_related('company')
    if company:
        qs = qs.filter(company=company)
    return qs.filter(id=location_id).first()


def get_locations_queryset(company: Company, filters: Optional[Dict[str, Any]] = None) -> QuerySet:
    """
    Returns an annotated Location queryset for the given tenant company
    with precomputed aggregation counts (routers, hotspots, active sessions)
    avoiding N+1 queries.
    """
    filters = filters or {}
    qs = Location.objects.filter(company=company).annotate(
        router_count=Count('routers', distinct=True),
        online_router_count=Count(
            'routers',
            filter=Q(routers__is_active=True, routers__health_status=RouterHealthStatus.ONLINE),
            distinct=True
        ),
        degraded_router_count=Count(
            'routers',
            filter=Q(routers__is_active=True, routers__health_status=RouterHealthStatus.DEGRADED),
            distinct=True
        ),
        unreachable_router_count=Count(
            'routers',
            filter=Q(
                routers__is_active=True,
                routers__health_status__in=[RouterHealthStatus.UNREACHABLE, RouterHealthStatus.OFFLINE]
            ),
            distinct=True
        ),
        hotspot_count=Count('hotspots', distinct=True),
        active_hotspot_count=Count('hotspots', filter=Q(hotspots__is_active=True), distinct=True),
        active_session_count=Count(
            'hotspots__sessions',
            filter=Q(hotspots__sessions__status=SessionStatus.ACTIVE),
            distinct=True
        ),
    )

    # Filter: status
    status_val = filters.get('status')
    if status_val:
        qs = qs.filter(status__iexact=status_val.strip())

    # Filter: site_type
    site_type = filters.get('site_type')
    if site_type:
        qs = qs.filter(site_type__iexact=site_type.strip())

    # Filter: region
    region = filters.get('region')
    if region:
        qs = qs.filter(region__icontains=region.strip())

    # Filter: district
    district = filters.get('district')
    if district:
        qs = qs.filter(district__icontains=district.strip())

    # Filter: is_active
    is_active = filters.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            qs = qs.filter(is_active=(is_active.lower() == 'true'))
        else:
            qs = qs.filter(is_active=bool(is_active))

    # Filter: search
    search = filters.get('search')
    if search:
        s = search.strip()
        qs = qs.filter(
            Q(name__icontains=s) |
            Q(code__icontains=s) |
            Q(region__icontains=s) |
            Q(district__icontains=s) |
            Q(address__icontains=s) |
            Q(contact_person__icontains=s) |
            Q(external_reference__icontains=s)
        )

    # Sorting
    ordering = filters.get('ordering', 'name')
    allowed_orderings = {
        'name', '-name',
        'code', '-code',
        'created_at', '-created_at',
        'region', '-region',
        'status', '-status',
        'site_type', '-site_type',
    }
    if ordering in allowed_orderings:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('name')

    return qs