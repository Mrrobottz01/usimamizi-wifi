import re
from typing import List, Optional

from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.vouchers.models import Voucher

from ..adapters.base import SMSErrorCategory, SMSProviderAdapter
from ..adapters.beem import BeemAfricaSMSAdapter
from ..adapters.mock import MockSMSProviderAdapter
from ..adapters.nextsms import NextSMSTanzaniaAdapter
from ..adapters.rafikisms import RafikiSMSAdapter
from ..models import (
    DeliveryAttemptStatus,
    NotificationDeliveryAttempt,
    NotificationMessage,
    NotificationProviderConfiguration,
    NotificationStatus,
    NotificationTemplate,
    SMSProviderSenderID,
    SMSProviderType,
    TenantSMSSenderPreference,
)


def normalize_phone_number(raw_phone: str, default_country_code: str = '255') -> str:
    """
    Centralized phone number normalization into E.164 canonical format (+255712345678).
    """
    clean = re.sub(r'[^\d+]', '', raw_phone.strip())
    if not clean:
        return ''

    if clean.startswith('+'):
        return clean

    if clean.startswith('0'):
        return f"+{default_country_code}{clean[1:]}"

    if clean.startswith(default_country_code):
        return f"+{clean}"

    if len(clean) == 9 and clean.startswith(('6', '7')):
        return f"+{default_country_code}{clean}"

    return f"+{clean}"


def _get_adapter_for_provider_type(provider_type: str) -> SMSProviderAdapter:
    """
    Factory resolving provider adapter instance.
    """
    if provider_type == SMSProviderType.BEEM:
        return BeemAfricaSMSAdapter()
    elif provider_type == SMSProviderType.NEXTSMS:
        return NextSMSTanzaniaAdapter()
    elif provider_type == SMSProviderType.RAFIKISMS:
        return RafikiSMSAdapter()
    else:
        return MockSMSProviderAdapter()


@transaction.atomic
def sync_provider_sender_ids(*, provider_config: NotificationProviderConfiguration) -> List[SMSProviderSenderID]:
    """
    Query provider for approved sender IDs, synchronize local cache, and update metadata.
    """
    adapter = _get_adapter_for_provider_type(provider_config.provider_type)
    discovered_senders = adapter.list_sender_ids(provider_config)

    current_sender_ids = set()
    for item in discovered_senders:
        current_sender_ids.add(item.sender_id)
        sender_obj, _ = SMSProviderSenderID.objects.get_or_create(
            provider_configuration=provider_config,
            sender_id=item.sender_id,
            defaults={
                'external_id': item.external_id,
                'display_name': item.display_name or item.sender_id,
                'status': item.status,
                'is_available': item.is_active,
            }
        )
        sender_obj.external_id = item.external_id
        sender_obj.display_name = item.display_name or item.sender_id
        sender_obj.status = item.status
        sender_obj.is_available = item.is_active
        sender_obj.save()

    # Mark senders not returned in current upstream query as unavailable
    SMSProviderSenderID.objects.filter(
        provider_configuration=provider_config
    ).exclude(
        sender_id__in=current_sender_ids
    ).update(is_available=False)

    # Ensure a default sender exists if none is set
    default_sender = SMSProviderSenderID.objects.filter(
        provider_configuration=provider_config,
        is_default=True,
        is_available=True
    ).first()

    if not default_sender:
        first_available = SMSProviderSenderID.objects.filter(
            provider_configuration=provider_config,
            is_available=True
        ).first()
        if first_available:
            first_available.is_default = True
            first_available.save()
            provider_config.default_sender_id = first_available.sender_id

    provider_config.last_sender_sync_at = timezone.now()
    provider_config.save()

    return list(SMSProviderSenderID.objects.filter(provider_configuration=provider_config))


def resolve_sender_id(
    *,
    company: Optional[Company],
    provider_config: NotificationProviderConfiguration,
    preferred_sender: str = ''
) -> str:
    """
    Hierarchical provider-specific sender resolution rule:
    1. Explicit preferred sender (if valid for this provider)
    2. Tenant override (if set and valid for this provider)
    3. Provider default synced sender ID
    4. First available provider sender ID
    5. Fallback configured provider sender ID
    """
    available_sids = set(
        SMSProviderSenderID.objects.filter(
            provider_configuration=provider_config,
            is_available=True
        ).values_list('sender_id', flat=True)
    )

    # 1. Preferred sender if requested and validated
    if preferred_sender and (not available_sids or preferred_sender in available_sids):
        return preferred_sender

    # 2. Tenant override
    if company:
        pref = TenantSMSSenderPreference.objects.filter(
            company=company,
            provider_code=provider_config.code
        ).first()
        if pref and (not available_sids or pref.sender_id in available_sids):
            return pref.sender_id

    # 3. Provider default sender ID
    if provider_config.default_sender_id and (not available_sids or provider_config.default_sender_id in available_sids):
        return provider_config.default_sender_id

    # 4. Default synced sender object
    default_obj = SMSProviderSenderID.objects.filter(
        provider_configuration=provider_config,
        is_default=True,
        is_available=True
    ).first()
    if default_obj:
        return default_obj.sender_id

    # 5. First available synced sender
    first_obj = SMSProviderSenderID.objects.filter(
        provider_configuration=provider_config,
        is_available=True
    ).first()
    if first_obj:
        return first_obj.sender_id

    # 6. Fallback from configuration
    return provider_config.sender_id or 'USIMAMIZI'


def route_and_send_sms(
    *,
    notification_message: NotificationMessage,
    target_provider_code: str = '',
    preferred_sender_id: str = ''
) -> NotificationMessage:
    """
    Execute priority-ordered SMS provider routing with multi-provider failover and sender snapshotting.
    """
    notification_message.status = NotificationStatus.SENDING
    notification_message.queued_at = timezone.now()
    notification_message.save()

    # Resolve active configurations ordered by priority
    configs = list(NotificationProviderConfiguration.objects.filter(
        is_active=True,
        channel='SMS'
    ).filter(
        company=notification_message.company
    ).order_by('priority'))

    if not configs:
        # Fallback to global default configurations (company=None)
        configs = list(NotificationProviderConfiguration.objects.filter(
            is_active=True,
            channel='SMS',
            company__isnull=True
        ).order_by('priority'))

    if target_provider_code:
        targeted = [c for c in configs if c.code == target_provider_code]
        if not targeted:
            direct_cfg = NotificationProviderConfiguration.objects.filter(code=target_provider_code).first()
            if direct_cfg:
                targeted = [direct_cfg]
        if targeted:
            configs = targeted

    if not configs:
        # Emergency Mock adapter fallback if no DB configs exist
        default_cfg = NotificationProviderConfiguration(
            name='Default Mock Provider',
            code='mock',
            provider_type=SMSProviderType.MOCK,
            priority=10
        )
        configs = [default_cfg]

    recipient = notification_message.phone_normalized or notification_message.recipient

    RECOVERABLE_FAILOVER_CATEGORIES = {
        SMSErrorCategory.PROVIDER_UNAVAILABLE,
        SMSErrorCategory.TIMEOUT,
        SMSErrorCategory.TEMPORARY_PROVIDER_ERROR,
        SMSErrorCategory.INSUFFICIENT_BALANCE,
        SMSErrorCategory.PROVIDER_RATE_LIMIT,
    }

    attempt_count = notification_message.attempts.count()
    message_sent = False

    for config in configs:
        attempt_count += 1
        adapter = _get_adapter_for_provider_type(config.provider_type)

        # Resolve provider-specific sender ID
        resolved_sender = resolve_sender_id(
            company=notification_message.company,
            provider_config=config,
            preferred_sender=preferred_sender_id
        )

        attempt = NotificationDeliveryAttempt.objects.create(
            company=notification_message.company,
            notification_message=notification_message,
            provider_code=config.code,
            sender_id=resolved_sender,
            attempt_number=attempt_count,
            status=DeliveryAttemptStatus.PENDING,
            started_at=timezone.now()
        )

        result = adapter.send_message(
            recipient_phone=recipient,
            message_text=notification_message.rendered_content,
            config=config,
            sender_id=resolved_sender
        )

        attempt.completed_at = timezone.now()
        attempt.provider_reference = result.provider_reference
        attempt.provider_status = result.provider_status
        attempt.failure_category = result.failure_category
        attempt.failure_code = result.failure_code
        attempt.failure_reason = result.failure_message

        if result.success:
            attempt.status = DeliveryAttemptStatus.SUCCESS
            attempt.save()

            notification_message.status = NotificationStatus.SENT
            notification_message.sent_at = timezone.now()
            notification_message.save()
            message_sent = True
            break
        else:
            attempt.status = DeliveryAttemptStatus.FAILED
            attempt.save()

            # Check if error category permits failover to next provider
            if result.failure_category not in RECOVERABLE_FAILOVER_CATEGORIES:
                break

    if not message_sent:
        notification_message.status = NotificationStatus.FAILED
        notification_message.failed_at = timezone.now()
        notification_message.save()

    return notification_message


@transaction.atomic
def send_voucher_sms(
    *,
    voucher: Voucher,
    recipient_phone: str,
    company: Company,
    template_code: str = 'VOUCHER_CREATED',
    language: str = 'en'
) -> NotificationMessage:
    """
    Queue and send voucher code via SMS.
    CRITICAL RULE: SMS delivery failure must NOT invalidate the voucher.
    """
    phone_norm = normalize_phone_number(recipient_phone)

    # Render template
    template = NotificationTemplate.objects.filter(
        company=company,
        code=template_code,
        language=language,
        is_active=True
    ).first()

    validity_str = f"{voucher.plan.duration_value} {voucher.plan.get_duration_unit_display()}"

    if template:
        body = template.body_template.replace('{{ voucher_code }}', voucher.display_code)
        body = body.replace('{{ plan_name }}', voucher.plan.name)
        body = body.replace('{{ validity }}', validity_str)
        body = body.replace('{{ ssid }}', 'Usimamizi-WiFi-Lab')
    else:
        # Default concise SMS content
        body = (
            f"Usimamizi Wi-Fi\n"
            f"Voucher: {voucher.display_code}\n"
            f"Package: {voucher.plan.name} ({validity_str})\n"
            f"Connect to Usimamizi-WiFi-Lab and enter your voucher code."
        )

    # Record recipient on voucher model
    voucher.recipient_phone = phone_norm
    voucher.save()

    # Create NotificationMessage
    notification_msg = NotificationMessage.objects.create(
        company=company,
        voucher=voucher,
        channel='SMS',
        recipient=recipient_phone,
        phone_normalized=phone_norm,
        template=template,
        rendered_content=body,
        status=NotificationStatus.QUEUED
    )

    # Dispatch SMS delivery
    route_and_send_sms(notification_message=notification_msg)

    return notification_msg
