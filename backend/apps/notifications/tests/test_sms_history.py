from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.companies.services.company_services import create_company
from apps.notifications.models import (
    DeliveryAttemptStatus,
    NotificationDeliveryAttempt,
    NotificationMessage,
    NotificationProviderConfiguration,
    NotificationStatus,
    SMSProviderType,
)
from apps.plans.models import Plan
from apps.vouchers.models import Voucher, VoucherBatch

User = get_user_model()


@pytest.fixture
def test_setup():
    user1 = User.objects.create_user(email='tenant1@example.com', password='Password123!')
    company1 = create_company(name='Alpha Hotspot Co', user=user1)

    user2 = User.objects.create_user(email='tenant2@example.com', password='Password123!')
    company2 = create_company(name='Beta Hotspot Co', user=user2)

    # Provider config for Company 1
    cfg = NotificationProviderConfiguration.objects.create(
        company=company1,
        name='RafikiSMS Primary',
        code='rafikisms',
        provider_type=SMSProviderType.RAFIKISMS,
        priority=1,
        is_active=True,
        default_sender_id='KOLOI TECH',
        encrypted_credentials={'api_key': 'sk_test_12345'}
    )

    plan = Plan.objects.create(
        company=company1,
        name='1 Hour High Speed',
        code='PLAN-1H',
        duration_value=1,
        duration_unit='HOURS',
        price='1000.00'
    )

    batch = VoucherBatch.objects.create(
        company=company1,
        plan=plan,
        quantity=5,
        reference='BATCH-001'
    )

    voucher = Voucher.objects.create(
        company=company1,
        batch=batch,
        plan=plan,
        code_hash='hash123',
        display_code='R2WS-VXSS',
        status='AVAILABLE'
    )

    # Message 1: Delivered with 2 attempts (Failover: Beem Failed -> Rafiki Delivered)
    msg1 = NotificationMessage.objects.create(
        company=company1,
        channel='SMS',
        recipient='0757047012',
        phone_normalized='+255757047012',
        voucher=voucher,
        rendered_content='Voucher Code: R2WS-VXSS',
        status=NotificationStatus.DELIVERED
    )
    NotificationDeliveryAttempt.objects.create(
        company=company1,
        notification_message=msg1,
        provider_code='beem',
        sender_id='BEEM_SENDER',
        attempt_number=1,
        status=DeliveryAttemptStatus.FAILED,
        failure_category='TIMEOUT',
        failure_reason='Gateway timeout'
    )
    NotificationDeliveryAttempt.objects.create(
        company=company1,
        notification_message=msg1,
        provider_code='rafikisms',
        sender_id='KOLOI TECH',
        attempt_number=2,
        status=DeliveryAttemptStatus.SUCCESS,
        provider_reference='19882233',
        provider_status='QUEUED'
    )

    # Message 2: Failed
    msg2 = NotificationMessage.objects.create(
        company=company1,
        channel='SMS',
        recipient='0712345678',
        phone_normalized='+255712345678',
        rendered_content='Failed SMS Alert',
        status=NotificationStatus.FAILED
    )
    NotificationDeliveryAttempt.objects.create(
        company=company1,
        notification_message=msg2,
        provider_code='rafikisms',
        sender_id='KOLOI TECH',
        attempt_number=1,
        status=DeliveryAttemptStatus.FAILED,
        failure_category='PROVIDER_RATE_LIMIT',
        failure_reason='HTTP 429 Too Many Requests'
    )

    # Message 3: Company 2 Message (Tenant Isolation Test)
    msg3 = NotificationMessage.objects.create(
        company=company2,
        channel='SMS',
        recipient='0788990011',
        phone_normalized='+255788990011',
        rendered_content='Company 2 Private Message',
        status=NotificationStatus.DELIVERED
    )

    return {
        'user1': user1,
        'company1': company1,
        'user2': user2,
        'company2': company2,
        'msg1': msg1,
        'msg2': msg2,
        'msg3': msg3,
        'voucher': voucher,
        'cfg': cfg,
    }


@pytest.mark.django_db
def test_sms_history_list_and_privacy_masking(test_setup):
    client = APIClient()
    client.force_authenticate(user=test_setup['user1'])
    company_id = test_setup['company1'].id

    res = client.get(f'/api/v1/notifications/sms/history/?company_id={company_id}')
    assert res.status_code == 200
    data = res.data

    assert data['count'] == 2
    assert len(data['results']) == 2
    assert data['summary']['total_messages'] == 2
    assert data['summary']['delivered'] == 1
    assert data['summary']['failed'] == 1
    assert data['summary']['delivery_rate'] == 50.0

    # Privacy masking verification
    first_item = data['results'][0]
    assert '****' in first_item['recipient_masked']

    # Voucher linkage check
    delivered_item = [r for r in data['results'] if r['id'] == str(test_setup['msg1'].id)][0]
    assert delivered_item['voucher_code'] == 'R2WS-VXSS'
    assert delivered_item['plan_name'] == '1 Hour High Speed'
    assert delivered_item['attempt_count'] == 2
    assert delivered_item['provider_used'] == 'rafikisms'


@pytest.mark.django_db
def test_sms_history_filters_and_search(test_setup):
    client = APIClient()
    client.force_authenticate(user=test_setup['user1'])
    company_id = test_setup['company1'].id

    # 1. Filter by Status = FAILED
    res_failed = client.get(f'/api/v1/notifications/sms/history/?company_id={company_id}&status=FAILED')
    assert res_failed.status_code == 200
    assert res_failed.data['count'] == 1
    assert res_failed.data['results'][0]['id'] == str(test_setup['msg2'].id)

    # 2. Search by Voucher Code
    res_search = client.get(f'/api/v1/notifications/sms/history/?company_id={company_id}&search=R2WS')
    assert res_search.status_code == 200
    assert res_search.data['count'] == 1
    assert res_search.data['results'][0]['voucher_code'] == 'R2WS-VXSS'


@pytest.mark.django_db
def test_sms_history_detail_and_failover_timeline(test_setup):
    client = APIClient()
    client.force_authenticate(user=test_setup['user1'])
    company_id = test_setup['company1'].id
    msg1_id = test_setup['msg1'].id

    res = client.get(f'/api/v1/notifications/sms/history/{msg1_id}/?company_id={company_id}')
    assert res.status_code == 200
    data = res.data

    assert data['id'] == str(msg1_id)
    assert data['phone_normalized'] == '+255757047012'
    assert data['voucher_code'] == 'R2WS-VXSS'
    assert data['can_retry'] is False  # Delivered message cannot be retried

    # Chronological Failover Delivery Attempts Verification
    attempts = data['attempts']
    assert len(attempts) == 2
    assert attempts[0]['attempt_number'] == 1
    assert attempts[0]['provider_code'] == 'beem'
    assert attempts[0]['status'] == 'FAILED'
    assert attempts[0]['failure_category'] == 'TIMEOUT'

    assert attempts[1]['attempt_number'] == 2
    assert attempts[1]['provider_code'] == 'rafikisms'
    assert attempts[1]['sender_id'] == 'KOLOI TECH'
    assert attempts[1]['status'] == 'SUCCESS'


@pytest.mark.django_db
def test_sms_history_tenant_isolation(test_setup):
    client = APIClient()
    # User 2 tries to access Company 1's SMS history
    client.force_authenticate(user=test_setup['user2'])
    company1_id = test_setup['company1'].id
    msg1_id = test_setup['msg1'].id

    # 1. List cross-tenant access denied
    res_list = client.get(f'/api/v1/notifications/sms/history/?company_id={company1_id}')
    assert res_list.status_code == 403

    # 2. Detail cross-tenant access denied
    res_detail = client.get(f'/api/v1/notifications/sms/history/{msg1_id}/?company_id={company1_id}')
    assert res_detail.status_code == 403

    # 3. Retry cross-tenant access denied
    res_retry = client.post(f'/api/v1/notifications/sms/history/{msg1_id}/retry/', data={'company_id': str(company1_id)})
    assert res_retry.status_code == 403


@pytest.mark.django_db
def test_sms_retry_failed_message_and_attempt_preservation(test_setup):
    client = APIClient()
    client.force_authenticate(user=test_setup['user1'])
    company_id = test_setup['company1'].id
    msg2_id = test_setup['msg2'].id

    # Mock successful retry via RafikiSMS
    mock_success = MagicMock()
    mock_success.read.return_value = b'{"status": "success", "data": {"sms_log_id": 776655}}'
    mock_success.__enter__.return_value = mock_success

    with patch('urllib.request.urlopen', return_value=mock_success):
        res_retry = client.post(
            f'/api/v1/notifications/sms/history/{msg2_id}/retry/',
            data={'company_id': str(company_id)},
            format='json'
        )
        assert res_retry.status_code == 200
        data = res_retry.data

        assert data['status'] == 'SENT'
        # Verification: Attempt #1 preserved, Attempt #2 appended
        assert len(data['attempts']) == 2
        assert data['attempts'][0]['attempt_number'] == 1
        assert data['attempts'][0]['status'] == 'FAILED'
        assert data['attempts'][1]['attempt_number'] == 2
        assert data['attempts'][1]['status'] == 'SUCCESS'


@pytest.mark.django_db
def test_sms_retry_delivered_message_blocked(test_setup):
    client = APIClient()
    client.force_authenticate(user=test_setup['user1'])
    company_id = test_setup['company1'].id
    msg1_id = test_setup['msg1'].id

    res_retry = client.post(
        f'/api/v1/notifications/sms/history/{msg1_id}/retry/',
        data={'company_id': str(company_id)},
        format='json'
    )
    assert res_retry.status_code == 400
    assert res_retry.data['code'] == 'invalid_retry'


@pytest.mark.django_db
def test_sms_history_export_csv(test_setup):
    client = APIClient()
    client.force_authenticate(user=test_setup['user1'])
    company_id = test_setup['company1'].id

    res = client.get(f'/api/v1/notifications/sms/history/export/?company_id={company_id}')
    assert res.status_code == 200
    assert res['Content-Type'] == 'text/csv'
    content = res.content.decode('utf-8')

    assert 'ID,Date Created,Recipient (Masked)' in content
    assert 'R2WS-VXSS' in content
    assert '1 Hour High Speed' in content
