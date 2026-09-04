import pytest
from django.contrib.auth import get_user_model

from apps.companies.services.company_services import create_company
from apps.notifications.models import (
    NotificationMessage,
    NotificationProviderConfiguration,
    NotificationStatus,
    SMSProviderType,
)
from apps.notifications.services.sms_services import (
    normalize_phone_number,
    route_and_send_sms,
    send_voucher_sms,
)
from apps.plans.services.plan_services import create_plan
from apps.vouchers.services.voucher_services import generate_voucher_batch

User = get_user_model()


def test_phone_normalization():
    assert normalize_phone_number('0712345678') == '+255712345678'
    assert normalize_phone_number('712345678') == '+255712345678'
    assert normalize_phone_number('255712345678') == '+255712345678'
    assert normalize_phone_number('+255712345678') == '+255712345678'


@pytest.mark.django_db
def test_route_and_send_sms_priority_and_failover():
    user = User.objects.create_user(email='sms_owner@example.com', password='Password123!')
    company = create_company(name='SMS Co', user=user)

    # Config 1: High priority Mock (will fail because phone contains 'fail_test')
    NotificationProviderConfiguration.objects.create(
        company=company,
        name='Priority 1 Mock',
        code='mock_primary',
        provider_type=SMSProviderType.MOCK,
        priority=1,
        is_active=True
    )

    # Config 2: Lower priority Mock (will succeed)
    NotificationProviderConfiguration.objects.create(
        company=company,
        name='Priority 2 Mock',
        code='mock_secondary',
        provider_type=SMSProviderType.MOCK,
        priority=2,
        is_active=True
    )

    # Message with failover trigger on primary
    msg = NotificationMessage.objects.create(
        company=company,
        channel='SMS',
        recipient='0712345678',
        phone_normalized='+255712345678',
        rendered_content='Test failover message',
        status=NotificationStatus.QUEUED
    )

    processed = route_and_send_sms(notification_message=msg)
    assert processed.status == NotificationStatus.SENT
    attempts = list(processed.attempts.all())
    assert len(attempts) == 2
    assert attempts[0].provider_code == 'mock_primary'
    assert attempts[0].status == 'FAILED'
    assert attempts[1].provider_code == 'mock_secondary'
    assert attempts[1].status == 'SUCCESS'


@pytest.mark.django_db
def test_sms_failure_does_not_invalidate_voucher():
    user = User.objects.create_user(email='sms_voucher@example.com', password='Password123!')
    company = create_company(name='Voucher SMS Co', user=user)
    plan = create_plan(company=company, data={'name': '1H Pass', 'code': 'LAB-1H', 'price': '1000.00'})
    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=1, created_by=user)
    voucher = vouchers[0]

    # Force provider failure
    NotificationProviderConfiguration.objects.all().delete()

    msg = send_voucher_sms(
        voucher=voucher,
        recipient_phone='0712345678',
        company=company
    )

    # Voucher status MUST remain AVAILABLE even if SMS delivery failed
    voucher.refresh_from_db()
    assert voucher.status == 'AVAILABLE'
    assert voucher.recipient_phone == '+255712345678'
    assert msg.rendered_content is not None
    assert voucher.display_code in msg.rendered_content
