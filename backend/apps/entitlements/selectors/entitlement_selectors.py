from datetime import datetime, timedelta
from typing import Any, Dict

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.companies.models import Company

from ..models import AccessEntitlement, EntitlementStatus


def get_entitlements_queryset(company: Company, filters: Dict[str, Any]) -> QuerySet:
    """
    Retrieve optimized, tenant-scoped QuerySet for Access Entitlements.
    """
    qs = AccessEntitlement.objects.filter(company=company)

    # Status filter
    status = filters.get('status')
    if status:
        qs = qs.filter(status=status)

    # Source Type filter
    source_type = filters.get('source_type')
    if source_type:
        qs = qs.filter(source_type=source_type)

    # Plan filter
    plan_id = filters.get('plan') or filters.get('plan_id')
    if plan_id:
        qs = qs.filter(plan_id=plan_id)

    # Voucher filter
    voucher_id = filters.get('voucher') or filters.get('voucher_id')
    if voucher_id:
        qs = qs.filter(voucher_id=voucher_id)

    voucher_code = filters.get('voucher_code')
    if voucher_code:
        qs = qs.filter(voucher__display_code__icontains=voucher_code)

    # Date range filters
    date_from = filters.get('date_from')
    if date_from:
        if isinstance(date_from, str):
            try:
                date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            except Exception:
                pass
        qs = qs.filter(created_at__gte=date_from)

    date_to = filters.get('date_to')
    if date_to:
        if isinstance(date_to, str):
            try:
                date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except Exception:
                pass
        qs = qs.filter(created_at__lte=date_to)

    expires_before = filters.get('expires_before')
    if expires_before:
        if isinstance(expires_before, str):
            try:
                expires_before = datetime.fromisoformat(expires_before.replace('Z', '+00:00'))
            except Exception:
                pass
        qs = qs.filter(expires_at__lte=expires_before)

    expires_after = filters.get('expires_after')
    if expires_after:
        if isinstance(expires_after, str):
            try:
                expires_after = datetime.fromisoformat(expires_after.replace('Z', '+00:00'))
            except Exception:
                pass
        qs = qs.filter(expires_at__gte=expires_after)

    # Global search query
    search = filters.get('search')
    if search:
        search = search.strip()
        qs = qs.filter(
            Q(reference__icontains=search) |
            Q(voucher__display_code__icontains=search) |
            Q(plan__name__icontains=search) |
            Q(plan__code__icontains=search) |
            Q(suspension_reason__icontains=search) |
            Q(revocation_reason__icontains=search)
        )

    # Sorting
    sort_by = filters.get('sort_by', '-created_at')
    allowed_sort_fields = [
        'created_at', '-created_at',
        'activated_at', '-activated_at',
        'expires_at', '-expires_at',
        'status', '-status',
        'reference', '-reference'
    ]
    if sort_by in allowed_sort_fields:
        qs = qs.order_by(sort_by)
    else:
        qs = qs.order_by('-created_at')

    return qs.select_related(
        'plan',
        'voucher',
        'voucher__batch',
        'customer',
        'created_by',
        'suspended_by',
        'revoked_by'
    ).distinct()


def calculate_entitlement_summary_metrics(company: Company, queryset: QuerySet = None) -> Dict[str, Any]:
    """
    Compute operational metrics for Access Entitlements.
    """
    if queryset is None:
        queryset = AccessEntitlement.objects.filter(company=company)

    total = queryset.count()
    counts = queryset.values('status').annotate(count=Count('id'))
    status_map = {c['status']: c['count'] for c in counts}

    now = timezone.now()
    soon_threshold = now + timedelta(hours=24)
    expiring_soon_count = queryset.filter(
        status=EntitlementStatus.ACTIVE,
        expires_at__gt=now,
        expires_at__lte=soon_threshold
    ).count()

    return {
        "total_entitlements": total,
        "active": status_map.get(EntitlementStatus.ACTIVE, 0),
        "expiring_soon": expiring_soon_count,
        "suspended": status_map.get(EntitlementStatus.SUSPENDED, 0),
        "expired": status_map.get(EntitlementStatus.EXPIRED, 0),
        "revoked": status_map.get(EntitlementStatus.REVOKED, 0),
        "pending": status_map.get(EntitlementStatus.PENDING, 0),
    }
