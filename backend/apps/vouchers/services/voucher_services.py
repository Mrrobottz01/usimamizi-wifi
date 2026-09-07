import csv
import io
import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.companies.models import Company
from apps.plans.models import Plan

from ..models import (
    Voucher,
    VoucherBatch,
    VoucherDistributionState,
    VoucherExportStatus,
    VoucherStatus,
)
from ..selectors.voucher_selectors import hash_voucher_code, normalize_voucher_code

# Safe characters excluding ambiguous characters (0, O, 1, I, L)
SAFE_VOUCHER_CHARS = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")


def generate_single_voucher_code(group_length: int = 4, groups: int = 2) -> str:
    """
    Generate a cryptographically secure random voucher code (e.g. K7PM-4XQ9).
    """
    parts = ["".join(secrets.choice(SAFE_VOUCHER_CHARS) for _ in range(group_length)) for _ in range(groups)]
    return "-".join(parts)


def _generate_batch_reference(company: Company) -> str:
    """
    Generate concurrency-safe batch reference string: VB-YYYYMMDD-XXXXXX
    """
    date_str = datetime.now().strftime("%Y%m%d")
    random_part = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"VB-{date_str}-{random_part}"


@transaction.atomic
def generate_voucher_batch(
    *,
    company: Company,
    plan: Plan,
    quantity: int,
    created_by=None,
    label: str = '',
    notes: str = '',
    distribution_mode: str = VoucherDistributionState.UNSOLD,
    expires_at=None
) -> Tuple[VoucherBatch, List[Voucher]]:
    """
    Generate a new batch of vouchers atomically for a company.
    """
    if quantity < 1 or quantity > 5000:
        raise ValidationError({'quantity': 'Quantity must be between 1 and 5000.'})

    if plan.company_id != company.id:
        raise ValidationError({'plan': 'Plan does not belong to the specified company.'})

    if not plan.is_active:
        raise ValidationError({'plan': 'Cannot generate vouchers for an inactive plan.'})

    dist_mode = distribution_mode if distribution_mode in VoucherDistributionState.values else VoucherDistributionState.UNSOLD

    # Create batch record
    batch_ref = _generate_batch_reference(company)
    batch = VoucherBatch.objects.create(
        company=company,
        plan=plan,
        reference=batch_ref,
        label=label.strip(),
        notes=notes.strip(),
        quantity=quantity,
        distribution_mode=dist_mode,
        expires_at=expires_at,
        created_by=created_by,
    )

    # Generate unique codes
    existing_codes = set(
        Voucher.objects.filter(company=company).values_list('display_code', flat=True)
    )

    vouchers_to_create = []
    generated_codes = set()

    for _ in range(quantity):
        while True:
            code = generate_single_voucher_code()
            if code not in existing_codes and code not in generated_codes:
                generated_codes.add(code)
                break

        vouchers_to_create.append(
            Voucher(
                company=company,
                batch=batch,
                plan=plan,
                display_code=code,
                code_hash=hash_voucher_code(code),
                status=VoucherStatus.AVAILABLE,
                distribution_state=dist_mode,
                expires_at=expires_at,
            )
        )

    vouchers = Voucher.objects.bulk_create(vouchers_to_create)

    # Create audit log
    AuditLog.objects.create(
        company=company,
        user=created_by,
        action="VOUCHER_BATCH_GENERATED",
        resource_type="VoucherBatch",
        resource_id=str(batch.id),
        changes={"batch_ref": batch_ref, "quantity": quantity, "plan_id": str(plan.id), "distribution_mode": dist_mode}
    )

    return batch, vouchers


@transaction.atomic
def reserve_voucher(
    *,
    voucher: Voucher,
    company: Company,
    customer_phone: str = '',
    reserved_by=None,
    distribution_state: Optional[str] = None
) -> Voucher:
    """
    Reserve an available voucher for a customer (e.g. pending distribution or payment).
    """
    if voucher.company_id != company.id:
        raise ValidationError({'voucher': 'Voucher does not belong to company.'})

    if voucher.status != VoucherStatus.AVAILABLE:
        raise ValidationError({'voucher': f'Cannot reserve voucher with status {voucher.status}.'})

    voucher.status = VoucherStatus.RESERVED
    voucher.reserved_at = timezone.now()
    if customer_phone:
        voucher.recipient_phone = customer_phone.strip()
    if distribution_state and distribution_state in VoucherDistributionState.values:
        voucher.distribution_state = distribution_state
    voucher.save()

    AuditLog.objects.create(
        company=company,
        user=reserved_by,
        action="VOUCHER_RESERVED",
        resource_type="Voucher",
        resource_id=str(voucher.id),
        changes={
            "recipient_phone": customer_phone,
            "distribution_state": voucher.distribution_state,
        }
    )

    return voucher


@transaction.atomic
def redeem_voucher(
    *,
    voucher_code: str,
    company: Company,
    customer_phone: str = ''
) -> Tuple[Voucher, Any]:
    """
    Redeem a voucher atomically with select_for_update concurrency lock.
    """
    canonical_code = normalize_voucher_code(voucher_code)
    code_h = hash_voucher_code(canonical_code)

    # Lock row for update
    voucher = Voucher.objects.select_for_update().filter(
        company=company,
        code_hash=code_h
    ).first()

    if not voucher:
        # Fallback to direct display_code lookup if code_hash differed
        voucher = Voucher.objects.select_for_update().filter(
            company=company,
            display_code=canonical_code
        ).first()

    if not voucher:
        raise ValidationError({'voucher': 'Voucher code not found.'})

    # Validate state machine transitions
    if voucher.status not in (VoucherStatus.AVAILABLE, VoucherStatus.RESERVED):
        if voucher.status == VoucherStatus.REDEEMED:
            raise ValidationError({'voucher': 'Voucher has already been redeemed.'})
        elif voucher.status == VoucherStatus.REVOKED:
            raise ValidationError({'voucher': 'Voucher has been revoked.'})
        elif voucher.status == VoucherStatus.EXPIRED:
            raise ValidationError({'voucher': 'Voucher has expired.'})
        else:
            raise ValidationError({'voucher': f'Voucher cannot be redeemed (status: {voucher.status}).'})

    if voucher.expires_at and voucher.expires_at < timezone.now():
        voucher.status = VoucherStatus.EXPIRED
        voucher.save()
        raise ValidationError({'voucher': 'Voucher has expired.'})

    from apps.entitlements.models import EntitlementSourceType
    from apps.entitlements.services.entitlement_services import create_entitlement_from_plan

    # 1. Create AccessEntitlement atomically with Plan snapshot
    entitlement = create_entitlement_from_plan(
        company=company,
        plan=voucher.plan,
        source_type=EntitlementSourceType.VOUCHER,
        voucher=voucher,
        activate_immediately=True
    )

    # 2. Transition to REDEEMED
    voucher.status = VoucherStatus.REDEEMED
    voucher.redeemed_at = timezone.now()
    if customer_phone and customer_phone.strip():
        voucher.redeemed_by_customer = customer_phone.strip()
        voucher.recipient_phone = customer_phone.strip()
    voucher.save()

    # 3. Create audit log
    AuditLog.objects.create(
        company=company,
        action="VOUCHER_REDEEMED",
        resource_type="Voucher",
        resource_id=str(voucher.id),
        changes={
            "code": voucher.display_code,
            "customer_phone": customer_phone,
            "entitlement_id": str(entitlement.id),
            "entitlement_reference": entitlement.reference,
        }
    )

    return voucher, entitlement


@transaction.atomic
def revoke_voucher(
    *,
    voucher: Voucher,
    company: Company,
    revoked_by=None,
    reason: str = ''
) -> Voucher:
    """
    Revoke a voucher. If voucher has already been redeemed, revokes the associated
    AccessEntitlement and immediately transmits an RFC 3576 Disconnect-Request (POD)
    to MikroTik to terminate active client sessions.
    """
    if voucher.company_id != company.id:
        raise ValidationError({'voucher': 'Voucher does not belong to company.'})

    if voucher.status == VoucherStatus.REVOKED:
        return voucher

    was_redeemed = (voucher.status == VoucherStatus.REDEEMED)

    voucher.status = VoucherStatus.REVOKED
    voucher.revoked_at = timezone.now()
    voucher.revoked_by = revoked_by
    voucher.revocation_reason = reason.strip()
    voucher.save()

    disconnected_sessions_count = 0

    # Cascading revocation for redeemed vouchers with active entitlement & session
    if was_redeemed and hasattr(voucher, 'entitlement') and voucher.entitlement:
        entitlement = voucher.entitlement
        if entitlement.status != 'REVOKED':
            entitlement.status = 'REVOKED'
            entitlement.revoked_at = timezone.now()
            entitlement.revoked_by = revoked_by
            entitlement.revocation_reason = reason.strip() or 'Revoked by administrator via voucher revocation'
            entitlement.save()

            try:
                from apps.hotspot_sessions.services.session_control import (
                    disconnect_active_sessions_for_entitlement,
                )
                disconnect_reqs = disconnect_active_sessions_for_entitlement(
                    entitlement=entitlement,
                    trigger_type='ADMIN_REVOCATION',
                    reason=reason.strip() or 'Voucher revoked by administrator',
                    requested_by=revoked_by
                )
                disconnected_sessions_count = len(disconnect_reqs)
            except Exception:
                pass

    AuditLog.objects.create(
        company=company,
        user=revoked_by,
        action="VOUCHER_REVOKED",
        resource_type="Voucher",
        resource_id=str(voucher.id),
        changes={
            "reason": reason,
            "was_redeemed": was_redeemed,
            "disconnected_sessions": disconnected_sessions_count
        }
    )

    return voucher


def export_batch_routeros_script(batch: VoucherBatch, profile_name: Optional[str] = None) -> str:
    """
    Generate RouterOS import command script (.rsc) for local lab HotSpot user export.
    Marks batch and vouchers as EXPORTED_ROUTEROS (local fallback mode).
    """
    vouchers = Voucher.objects.filter(batch=batch).order_by('display_code')
    profile = profile_name or (batch.plan.code if batch.plan else "default") or "default"

    # Mark as exported in SaaS
    batch.export_status = VoucherExportStatus.EXPORTED_ROUTEROS
    batch.save(update_fields=['export_status', 'updated_at'])
    Voucher.objects.filter(batch=batch).update(export_status=VoucherExportStatus.EXPORTED_ROUTEROS)

    lines = [
        "# ===================================================================",
        "# USIMAMIZI WI-FI - ROUTEROS LOCAL HOTSPOT FALLBACK USER EXPORT",
        f"# SOURCE: USIMAMIZI_LOCAL_FALLBACK | BATCH: {batch.reference}",
        f"# PLAN: {batch.plan.name} ({batch.plan.code})",
        f"# GENERATED AT: {timezone.now().isoformat()}",
        f"# TOTAL USERS: {len(vouchers)}",
        "# NOTE: Use only during central SaaS outage or isolated offline nodes.",
        "# ===================================================================",
        "",
    ]

    for v in vouchers:
        cmd = (
            f'/ip hotspot user add name="{v.display_code}" password="{v.display_code}" '
            f'profile="{profile}" comment="USIMAMIZI_FALLBACK Batch: {batch.reference}"'
        )
        lines.append(cmd)

    lines.append("")
    return "\n".join(lines)


def export_batch_csv(batch: VoucherBatch) -> str:
    """
    Export voucher batch details to CSV string with comprehensive metadata.
    """
    vouchers = Voucher.objects.filter(batch=batch).order_by('display_code')
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'code',
        'plan_name',
        'plan_code',
        'batch_ref',
        'status',
        'distribution_state',
        'export_status',
        'recipient_phone',
        'expires_at',
        'created_at'
    ])
    for v in vouchers:
        writer.writerow([
            v.display_code,
            batch.plan.name,
            batch.plan.code,
            batch.reference,
            v.status,
            v.distribution_state,
            v.export_status,
            v.recipient_phone,
            v.expires_at.isoformat() if v.expires_at else '',
            v.created_at.isoformat(),
        ])

    return output.getvalue()


def get_printable_voucher_cards(
    batch: VoucherBatch,
    portal_base_url: str = 'http://login.usimamizi.lab:5173',
    hotspot: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Generate structured data for rendering A4 multi-card printable voucher sheets.
    """
    from apps.companies.services.portal_services import get_default_hotspot

    if hotspot is None:
        hotspot = get_default_hotspot(batch.company)

    ssid = hotspot.ssid if (hotspot and getattr(hotspot, 'ssid', None)) else "Usimamizi-WiFi-Lab"
    portal_slug = hotspot.slug if (hotspot and getattr(hotspot, 'slug', None)) else batch.company.slug
    domain_display = getattr(hotspot, 'dns_name', None) or getattr(hotspot, 'gateway_ip', None) or "login.usimamizi.lab"

    vouchers = Voucher.objects.filter(batch=batch).order_by('display_code')
    validity_display = f"{batch.plan.duration_value} {batch.plan.get_duration_unit_display()}"

    cards = []
    for v in vouchers:
        cards.append({
            "id": str(v.id),
            "code": v.display_code,
            "plan_name": batch.plan.name,
            "validity": validity_display,
            "duration_display": validity_display,
            "price": str(batch.plan.price),
            "currency": batch.plan.currency,
            "speed": f"{round(batch.plan.download_speed_kbps/1000, 1)}M Down" if batch.plan.download_speed_kbps else "Uncapped",
            "speed_display": f"{round(batch.plan.download_speed_kbps/1000, 1)}M Down" if batch.plan.download_speed_kbps else "Uncapped",
            "quota_display": f"{round(batch.plan.data_limit_bytes/(1024*1024), 0)}MB" if batch.plan.data_limit_bytes else "Unlimited",
            "devices": batch.plan.max_devices,
            "ssid": ssid,
            "batch_ref": batch.reference,
            "qr_url": f"{portal_base_url}/p/{portal_slug}?voucher={v.display_code}",
            "instructions": f"1. Connect to {ssid}\n2. Open {domain_display}\n3. Enter this voucher code"
        })

    return cards

