from decimal import Decimal
from typing import Any, Dict

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.companies.models import Company

from ..models import Plan


@transaction.atomic
def create_plan(*, company: Company, data: Dict[str, Any]) -> Plan:
    """
    Create a new commercial internet access plan for a company.
    """
    price = Decimal(str(data.get('price', '0.00')))
    if price < Decimal('0.00'):
        raise ValidationError({'price': 'Price cannot be negative.'})

    max_devices = int(data.get('max_devices', 1))
    if max_devices < 1:
        raise ValidationError({'max_devices': 'Max devices must be at least 1.'})

    simultaneous_sessions = int(data.get('simultaneous_sessions', 1))
    if simultaneous_sessions < 1:
        raise ValidationError({'simultaneous_sessions': 'Simultaneous sessions must be at least 1.'})

    code = data.get('code', '').strip()
    if not code:
        raise ValidationError({'code': 'Plan code is required.'})

    if Plan.objects.filter(company=company, code__iexact=code).exists():
        raise ValidationError({'code': f"Plan with code '{code}' already exists for this company."})

    plan = Plan.objects.create(
        company=company,
        name=data.get('name', '').strip(),
        code=code.upper(),
        description=data.get('description', '').strip(),
        price=price,
        currency=data.get('currency', 'TZS').upper(),
        duration_value=int(data.get('duration_value', 1)),
        duration_unit=data.get('duration_unit', 'HOURS'),
        validity_mode=data.get('validity_mode', 'CONTINUOUS'),
        download_speed_kbps=data.get('download_speed_kbps'),
        upload_speed_kbps=data.get('upload_speed_kbps'),
        data_limit_bytes=data.get('data_limit_bytes'),
        max_devices=max_devices,
        simultaneous_sessions=simultaneous_sessions,
        idle_timeout_seconds=data.get('idle_timeout_seconds'),
        session_timeout_seconds=data.get('session_timeout_seconds'),
        is_active=data.get('is_active', True),
        sort_order=int(data.get('sort_order', 0)),
    )

    return plan


@transaction.atomic
def update_plan(*, plan: Plan, data: Dict[str, Any]) -> Plan:
    """
    Update plan details.
    """
    if 'price' in data:
        price = Decimal(str(data['price']))
        if price < Decimal('0.00'):
            raise ValidationError({'price': 'Price cannot be negative.'})
        plan.price = price

    if 'name' in data:
        plan.name = data['name'].strip()

    if 'description' in data:
        plan.description = data['description'].strip()

    if 'download_speed_kbps' in data:
        plan.download_speed_kbps = data['download_speed_kbps']

    if 'upload_speed_kbps' in data:
        plan.upload_speed_kbps = data['upload_speed_kbps']

    if 'max_devices' in data:
        plan.max_devices = max(1, int(data['max_devices']))

    if 'is_active' in data:
        plan.is_active = bool(data['is_active'])

    plan.save()
    return plan


@transaction.atomic
def deactivate_plan(*, plan: Plan) -> Plan:
    """
    Deactivate a plan so it cannot be used for new voucher batches.
    """
    plan.is_active = False
    plan.save()
    return plan
