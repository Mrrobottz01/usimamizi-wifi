import hashlib
import re
from typing import Any, Dict, List, Optional

from django.db.models import Count, Q, QuerySet

from apps.companies.models import Company

from ..models import (
    Voucher,
    VoucherBatch,
    VoucherDistributionState,
    VoucherExportStatus,
    VoucherStatus,
)


def normalize_voucher_code(code: str) -> str:
    """
    Standardize user input into canonical uppercase voucher format (e.g. ABCD-7XQ9).
    Accepts lowercase, spaces, missing hyphens (abcd 7xq9, abcd7xq9 -> ABCD-7XQ9).
    """
    if not code:
        return ''
    clean = re.sub(r'[^A-Za-z0-9]', '', code.strip()).upper()
    if len(clean) == 8:
        return f"{clean[:4]}-{clean[4:]}"
    elif len(clean) == 12:
        return f"{clean[:4]}-{clean[4:8]}-{clean[8:]}"
    return code.strip().upper()


def hash_voucher_code(code: str) -> str:
    """
    Generate SHA256 hash of normalized uppercase voucher code.
    """
    canonical = normalize_voucher_code(code)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def get_batches_for_company(company: Company) -> QuerySet[VoucherBatch]:
    """
    Retrieve all voucher batches belonging to a company with cached voucher counts.
    """
    return VoucherBatch.objects.filter(
        company=company
    ).select_related('plan', 'created_by').annotate(
        total_vouchers=Count('vouchers'),
        redeemed_vouchers=Count('vouchers', filter=Q(vouchers__status=VoucherStatus.REDEEMED)),
        available_vouchers=Count('vouchers', filter=Q(vouchers__status=VoucherStatus.AVAILABLE)),
    ).order_by('-created_at')


def get_batch_by_id(batch_id: str, company: Optional[Company] = None) -> Optional[VoucherBatch]:
    """
    Retrieve a voucher batch by ID with optional company boundary.
    """
    try:
        qs = VoucherBatch.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs.select_related('plan', 'company', 'created_by').get(id=batch_id)
    except (VoucherBatch.DoesNotExist, ValueError):
        return None


def get_vouchers_for_batch(batch: VoucherBatch) -> QuerySet[Voucher]:
    """
    Retrieve vouchers for a specific batch.
    """
    return Voucher.objects.filter(batch=batch).select_related('plan', 'revoked_by').order_by('-created_at')


def get_voucher_by_code(code: str, company: Optional[Company] = None) -> Optional[Voucher]:
    """
    Retrieve voucher by display code or code hash using normalized code matching.
    """
    canonical = normalize_voucher_code(code)
    code_h = hash_voucher_code(canonical)

    qs = Voucher.objects.filter(Q(display_code=canonical) | Q(code_hash=code_h))
    if company:
        qs = qs.filter(company=company)

    return qs.select_related('plan', 'company', 'batch', 'revoked_by').first()


def search_vouchers(
    company: Company,
    query: str = '',
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    distribution_state: Optional[str] = None,
    export_status: Optional[str] = None
) -> QuerySet[Voucher]:
    """
    Search and filter vouchers with strict tenant isolation.
    """
    qs = Voucher.objects.filter(company=company).select_related('plan', 'batch', 'revoked_by')

    if query.strip():
        q_clean = query.strip()
        canonical_q = normalize_voucher_code(q_clean)
        qs = qs.filter(
            Q(display_code__icontains=q_clean) |
            Q(display_code__icontains=canonical_q) |
            Q(recipient_phone__icontains=q_clean) |
            Q(batch__reference__icontains=q_clean)
        )

    if status and status in VoucherStatus.values:
        qs = qs.filter(status=status)

    if batch_id:
        qs = qs.filter(batch_id=batch_id)

    if plan_id:
        qs = qs.filter(plan_id=plan_id)

    if distribution_state and distribution_state in VoucherDistributionState.values:
        qs = qs.filter(distribution_state=distribution_state)

    if export_status and export_status in VoucherExportStatus.values:
        qs = qs.filter(export_status=export_status)

    return qs.order_by('-created_at')


def get_voucher_metrics(company: Company) -> Dict[str, Any]:
    """
    Compute comprehensive SaaS voucher metrics for dashboard.
    """
    qs = Voucher.objects.filter(company=company)
    total = qs.count()
    available = qs.filter(status=VoucherStatus.AVAILABLE).count()
    reserved = qs.filter(status=VoucherStatus.RESERVED).count()
    redeemed = qs.filter(status=VoucherStatus.REDEEMED).count()
    expired = qs.filter(status=VoucherStatus.EXPIRED).count()
    revoked = qs.filter(status=VoucherStatus.REVOKED).count()

    sent_sms = qs.exclude(recipient_phone='').count()
    exported = qs.filter(export_status=VoucherExportStatus.EXPORTED_ROUTEROS).count()

    sold = qs.filter(distribution_state=VoucherDistributionState.SOLD).count()
    unsold = qs.filter(distribution_state=VoucherDistributionState.UNSOLD).count()
    free = qs.filter(distribution_state=VoucherDistributionState.GIVEN_FREE).count()

    redemption_rate = round((redeemed / total * 100.0), 1) if total > 0 else 0.0

    return {
        "total": total,
        "available": available,
        "reserved": reserved,
        "redeemed": redeemed,
        "expired": expired,
        "revoked": revoked,
        "sent_sms": sent_sms,
        "exported_routeros": exported,
        "sold": sold,
        "unsold": unsold,
        "free": free,
        "redemption_rate": redemption_rate,
    }


def get_voucher_timeline(voucher: Voucher) -> List[Dict[str, Any]]:
    """
    Build chronological lifecycle audit timeline for a voucher.
    """
    events = []

    # 1. Created
    events.append({
        "event": "VOUCHER_CREATED",
        "timestamp": voucher.created_at.isoformat(),
        "title": "Voucher Created",
        "description": f"Generated in batch {voucher.batch.reference} for plan {voucher.plan.name}.",
        "status": "success"
    })

    # 2. Exported to RouterOS
    if voucher.export_status == VoucherExportStatus.EXPORTED_ROUTEROS:
        events.append({
            "event": "VOUCHER_EXPORTED",
            "timestamp": voucher.updated_at.isoformat(),
            "title": "Exported to RouterOS",
            "description": "Exported for local offline hotspot fallback.",
            "status": "info"
        })

    # 3. Reserved
    if voucher.reserved_at:
        events.append({
            "event": "VOUCHER_RESERVED",
            "timestamp": voucher.reserved_at.isoformat(),
            "title": "Voucher Reserved",
            "description": f"Reserved for customer distribution ({voucher.recipient_phone or 'No phone'}).",
            "status": "info"
        })

    # 4. SMS Delivery attempts
    try:
        from apps.notifications.models import NotificationMessage
        sms_msgs = NotificationMessage.objects.filter(voucher=voucher).order_by('created_at')
        for msg in sms_msgs:
            events.append({
                "event": "SMS_DISPATCHED",
                "timestamp": msg.created_at.isoformat(),
                "title": f"SMS {msg.status}",
                "description": f"Sent to {msg.phone_normalized or msg.recipient} via {getattr(msg, 'channel', 'SMS')}.",
                "status": "success" if msg.status == 'DELIVERED' else ("warning" if msg.status == 'SENT' else "error")
            })
    except Exception:
        pass

    # 5. Redeemed & Entitlement
    if voucher.redeemed_at:
        entitlement_ref = ""
        try:
            if hasattr(voucher, 'entitlement') and voucher.entitlement:
                entitlement_ref = f" (Entitlement: {voucher.entitlement.reference})"
        except Exception:
            pass

        events.append({
            "event": "VOUCHER_REDEEMED",
            "timestamp": voucher.redeemed_at.isoformat(),
            "title": "Voucher Redeemed",
            "description": f"Redeemed by {voucher.redeemed_by_customer or 'Customer'}{entitlement_ref}. Access granted.",
            "status": "success"
        })

    # 6. Physical RADIUS Hotspot Sessions
    try:
        if hasattr(voucher, 'entitlement') and voucher.entitlement:
            from apps.hotspot_sessions.models import HotspotSession
            sessions = HotspotSession.objects.filter(entitlement=voucher.entitlement).order_by('started_at')
            for s in sessions:
                events.append({
                    "event": "SESSION_RECORDED",
                    "timestamp": s.started_at.isoformat(),
                    "title": f"Session {s.status}",
                    "description": f"IP: {s.framed_ip_address} | MAC: {s.mac_address} | Data: {round((s.total_bytes or 0)/1024/1024, 2)} MB",
                    "status": "success" if s.status == 'ACTIVE' else "info"
                })
    except Exception:
        pass

    # 7. Revoked
    if voucher.revoked_at:
        events.append({
            "event": "VOUCHER_REVOKED",
            "timestamp": voucher.revoked_at.isoformat(),
            "title": "Voucher Revoked",
            "description": f"Revoked: {voucher.revocation_reason or 'No reason specified'} by {voucher.revoked_by or 'Admin'}.",
            "status": "error"
        })

    # 8. Expired
    if voucher.status == VoucherStatus.EXPIRED:
        events.append({
            "event": "VOUCHER_EXPIRED",
            "timestamp": voucher.expires_at.isoformat() if voucher.expires_at else voucher.updated_at.isoformat(),
            "title": "Voucher Expired",
            "description": "Voucher passed validity deadline without redemption.",
            "status": "warning"
        })

    # Sort events chronologically
    return sorted(events, key=lambda x: x["timestamp"])

