from datetime import datetime
from typing import Any, Dict

from django.db.models import Count, Q, QuerySet

from apps.companies.models import Company

from ..models import NotificationMessage, NotificationStatus


def get_sms_history_queryset(company: Company, filters: Dict[str, Any]) -> QuerySet:
    """
    Retrieve optimized, tenant-scoped QuerySet for SMS notification history.
    """
    qs = NotificationMessage.objects.filter(company=company, channel='SMS')

    # Status filter
    status = filters.get('status')
    if status:
        qs = qs.filter(status=status)

    if filters.get('failed_only'):
        qs = qs.filter(status=NotificationStatus.FAILED)
    elif filters.get('delivered_only'):
        qs = qs.filter(status=NotificationStatus.DELIVERED)

    # Provider code filter
    provider = filters.get('provider')
    if provider:
        qs = qs.filter(attempts__provider_code=provider)

    # Sender ID filter
    sender_id = filters.get('sender_id')
    if sender_id:
        qs = qs.filter(attempts__sender_id=sender_id)

    # Message type / Template code filter
    template_code = filters.get('message_type') or filters.get('template_code')
    if template_code:
        qs = qs.filter(template__code=template_code)

    # Date range filter
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

    # Phone search / filter
    phone = filters.get('phone')
    if phone:
        qs = qs.filter(Q(recipient__icontains=phone) | Q(phone_normalized__icontains=phone))

    # Voucher search / filter
    voucher_code = filters.get('voucher_code')
    if voucher_code:
        qs = qs.filter(voucher__display_code__icontains=voucher_code)

    voucher_batch = filters.get('voucher_batch')
    if voucher_batch:
        qs = qs.filter(Q(voucher__batch_id=voucher_batch) | Q(voucher__batch__reference__icontains=voucher_batch))

    # Global search query
    search = filters.get('search')
    if search:
        search = search.strip()
        qs = qs.filter(
            Q(recipient__icontains=search) |
            Q(phone_normalized__icontains=search) |
            Q(voucher__display_code__icontains=search) |
            Q(attempts__provider_reference__icontains=search) |
            Q(rendered_content__icontains=search)
        )

    # Sorting
    sort_by = filters.get('sort_by', '-created_at')
    allowed_sort_fields = [
        'created_at', '-created_at',
        'sent_at', '-sent_at',
        'delivered_at', '-delivered_at',
        'status', '-status'
    ]
    if sort_by in allowed_sort_fields:
        qs = qs.order_by(sort_by)
    else:
        qs = qs.order_by('-created_at')

    return qs.select_related(
        'template',
        'voucher',
        'voucher__plan',
        'voucher__batch'
    ).prefetch_related(
        'attempts'
    ).distinct()


def calculate_sms_summary_metrics(company: Company, queryset: QuerySet = None) -> Dict[str, Any]:
    """
    Calculate summary metrics for SMS operations.
    Delivery Rate formula: delivered / (delivered + failed) * 100
    """
    if queryset is None:
        queryset = NotificationMessage.objects.filter(company=company, channel='SMS')

    total = queryset.count()
    counts = queryset.values('status').annotate(count=Count('id'))

    status_map = {c['status']: c['count'] for c in counts}

    delivered = status_map.get(NotificationStatus.DELIVERED, 0)
    sent = status_map.get(NotificationStatus.SENT, 0)
    failed = status_map.get(NotificationStatus.FAILED, 0)
    queued = status_map.get(NotificationStatus.QUEUED, 0)
    sending = status_map.get(NotificationStatus.SENDING, 0)

    # Calculate delivery rate based on terminal outcomes (delivered vs failed)
    terminal_total = delivered + failed
    if terminal_total > 0:
        delivery_rate = round((delivered / terminal_total) * 100.0, 1)
    else:
        delivery_rate = None

    return {
        "total_messages": total,
        "delivered": delivered,
        "sent": sent,
        "failed": failed,
        "queued": queued,
        "sending": sending,
        "delivery_rate": delivery_rate,
    }
