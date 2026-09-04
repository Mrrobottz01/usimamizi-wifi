import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.companies.services.company_services import create_company
from apps.notifications.adapters.base import SMSErrorCategory
from apps.notifications.adapters.rafikisms import RafikiSMSAdapter
from apps.notifications.models import (
    NotificationDeliveryAttempt,
    NotificationMessage,
    NotificationProviderConfiguration,
    NotificationStatus,
    SMSProviderType,
)
from apps.notifications.services.sms_services import route_and_send_sms, send_voucher_sms
from apps.plans.services.plan_services import create_plan
from apps.vouchers.models import VoucherStatus
from apps.vouchers.services.voucher_services import generate_voucher_batch

User = get_user_model()


class DummyConfig:
    def __init__(self, api_key='sk_test_12345', base_url='https://api.rafikisms.com', sender_id='USIMAMIZI'):
        self.code = 'rafikisms'
        self.base_url = base_url
        self.sender_id = sender_id
        self.encrypted_credentials = {'api_key': api_key}
        self.settings_json = {}


def test_rafikisms_phone_number_conversion():
    adapter = RafikiSMSAdapter()
    config = DummyConfig()

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "status": "success",
        "message": "SMS queued successfully",
        "data": {"sms_log_id": 19725260}
    }).encode('utf-8')
    mock_response.__enter__.return_value = mock_response

    with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
        result = adapter.send_message('+255712345678', 'Test message', config)

        assert result.success is True
        assert result.provider_reference == '19725260'
        assert result.delivery_status == 'SENT'

        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.headers.get('X-api-key') == 'sk_test_12345' or req_arg.headers.get('X-API-Key') == 'sk_test_12345'
        payload = json.loads(req_arg.data.decode('utf-8'))
        assert payload['phone'] == '255712345678'  # + sign removed at adapter boundary


def test_rafikisms_message_length_validation():
    adapter = RafikiSMSAdapter()
    config = DummyConfig()

    long_message = "A" * 161
    with patch('urllib.request.urlopen') as mock_urlopen:
        result = adapter.send_message('+255712345678', long_message, config)
        assert result.success is False
        assert result.failure_category == SMSErrorCategory.INVALID_REQUEST
        assert result.failure_code == 'MESSAGE_TOO_LONG'
        mock_urlopen.assert_not_called()


def test_rafikisms_missing_credentials():
    adapter = RafikiSMSAdapter()
    config = DummyConfig(api_key='')
    result = adapter.send_message('+255712345678', 'Test message', config)

    assert result.success is False
    assert result.failure_category == SMSErrorCategory.AUTHENTICATION_FAILED
    assert result.failure_code == 'MISSING_CREDENTIALS'


def test_rafikisms_http_401_authentication_failure():
    adapter = RafikiSMSAdapter()
    config = DummyConfig()

    err = urllib.error.HTTPError('https://api.rafikisms.com', 401, 'Unauthorized', {}, None)
    err.read = lambda: json.dumps({'message': 'Invalid API Key'}).encode('utf-8')

    with patch('urllib.request.urlopen', side_effect=err):
        result = adapter.send_message('+255712345678', 'Test message', config)
        assert result.success is False
        assert result.failure_category == SMSErrorCategory.AUTHENTICATION_FAILED
        assert result.failure_code == '401'


def test_rafikisms_http_400_invalid_request():
    adapter = RafikiSMSAdapter()
    config = DummyConfig()

    err = urllib.error.HTTPError('https://api.rafikisms.com', 400, 'Bad Request', {}, None)
    err.read = lambda: json.dumps({'message': 'Invalid recipient'}).encode('utf-8')

    with patch('urllib.request.urlopen', side_effect=err):
        result = adapter.send_message('+255712345678', 'Test message', config)
        assert result.success is False
        assert result.failure_category == SMSErrorCategory.INVALID_REQUEST
        assert result.failure_code == '400'


def test_rafikisms_http_429_rate_limit():
    adapter = RafikiSMSAdapter()
    config = DummyConfig()

    err = urllib.error.HTTPError('https://api.rafikisms.com', 429, 'Too Many Requests', {}, None)
    err.read = lambda: json.dumps({'message': 'Rate limit exceeded'}).encode('utf-8')

    with patch('urllib.request.urlopen', side_effect=err):
        result = adapter.send_message('+255712345678', 'Test message', config)
        assert result.success is False
        assert result.failure_category == SMSErrorCategory.PROVIDER_RATE_LIMIT
        assert result.failure_code == '429'


def test_rafikisms_http_500_temporary_error():
    adapter = RafikiSMSAdapter()
    config = DummyConfig()

    err = urllib.error.HTTPError('https://api.rafikisms.com', 500, 'Server Error', {}, None)
    err.read = lambda: json.dumps({'message': 'Internal Error'}).encode('utf-8')

    with patch('urllib.request.urlopen', side_effect=err):
        result = adapter.send_message('+255712345678', 'Test message', config)
        assert result.success is False
        assert result.failure_category == SMSErrorCategory.TEMPORARY_PROVIDER_ERROR
        assert result.failure_code == '500'


@pytest.mark.django_db
def test_rafikisms_webhook_delivery_and_idempotency():
    user = User.objects.create_user(email='webhook_user@example.com', password='Password123!')
    company = create_company(name='Webhook Co', user=user)

    msg = NotificationMessage.objects.create(
        company=company,
        channel='SMS',
        recipient='+255712345678',
        phone_normalized='+255712345678',
        rendered_content='Voucher: K7PM-4XQ9',
        status=NotificationStatus.SENT
    )

    NotificationDeliveryAttempt.objects.create(
        company=company,
        notification_message=msg,
        provider_code='rafikisms',
        attempt_number=1,
        status='SUCCESS',
        provider_reference='19725260'
    )

    client = APIClient()

    payload = {
        "event": "sms.delivery_status",
        "event_time": "2026-08-30T10:00:00Z",
        "data": {
            "sms_log_id": 19725260,
            "status": "delivered",
            "recipient": "255712345678",
            "transaction_id": "19725260"
        }
    }

    # Initial webhook call -> transitions to DELIVERED
    res1 = client.post('/api/v1/webhooks/sms/rafikisms/', data=payload, format='json')
    assert res1.status_code == 200
    msg.refresh_from_db()
    assert msg.status == NotificationStatus.DELIVERED

    # Duplicate webhook call -> remains DELIVERED, no error or duplicate attempt creation
    res2 = client.post('/api/v1/webhooks/sms/rafikisms/', data=payload, format='json')
    assert res2.status_code == 200
    msg.refresh_from_db()
    assert msg.status == NotificationStatus.DELIVERED
    assert msg.attempts.count() == 1


@pytest.mark.django_db
def test_rafikisms_failover_routing_scenarios():
    user = User.objects.create_user(email='failover_user@example.com', password='Password123!')
    company = create_company(name='Failover Co', user=user)

    # Priority 1: RafikiSMS (Fails with HTTP 429 Rate Limit)
    NotificationProviderConfiguration.objects.create(
        company=company,
        name='RafikiSMS Rate Limited',
        code='rafikisms_p1',
        provider_type=SMSProviderType.RAFIKISMS,
        priority=1,
        is_active=True,
        encrypted_credentials={'api_key': 'sk_p1'}
    )

    # Priority 2: Mock Provider (Succeeds)
    NotificationProviderConfiguration.objects.create(
        company=company,
        name='Mock Secondary',
        code='mock_p2',
        provider_type=SMSProviderType.MOCK,
        priority=2,
        is_active=True
    )

    err429 = urllib.error.HTTPError('https://api.rafikisms.com', 429, 'Rate Limit Exceeded', {}, None)
    err429.read = lambda: json.dumps({'message': 'Rate limit hit'}).encode('utf-8')

    with patch('urllib.request.urlopen', side_effect=err429):
        msg = NotificationMessage.objects.create(
            company=company,
            channel='SMS',
            recipient='+255712345678',
            phone_normalized='+255712345678',
            rendered_content='Test failover message',
            status=NotificationStatus.QUEUED
        )

        processed = route_and_send_sms(notification_message=msg)
        assert processed.status == NotificationStatus.SENT
        attempts = list(processed.attempts.all())
        assert len(attempts) == 2
        assert attempts[0].provider_code == 'rafikisms_p1'
        assert attempts[0].status == 'FAILED'
        assert attempts[0].failure_category == SMSErrorCategory.PROVIDER_RATE_LIMIT
        assert attempts[1].provider_code == 'mock_p2'
        assert attempts[1].status == 'SUCCESS'


@pytest.mark.django_db
def test_rafikisms_voucher_independence():
    user = User.objects.create_user(email='voucher_indep@example.com', password='Password123!')
    company = create_company(name='Voucher Indep Co', user=user)
    plan = create_plan(company=company, data={'name': '1H Pass', 'code': 'LAB-1H', 'price': '1000.00'})
    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=1, created_by=user)
    voucher = vouchers[0]

    # RafikiSMS config with invalid credentials to trigger send failure
    NotificationProviderConfiguration.objects.all().delete()
    NotificationProviderConfiguration.objects.create(
        company=company,
        name='RafikiSMS Failing',
        code='rafikisms_fail',
        provider_type=SMSProviderType.RAFIKISMS,
        priority=1,
        is_active=True,
        encrypted_credentials={'api_key': 'invalid_key'}
    )

    err401 = urllib.error.HTTPError('https://api.rafikisms.com', 401, 'Unauthorized', {}, None)
    err401.read = lambda: json.dumps({'message': 'Invalid API Key'}).encode('utf-8')

    with patch('urllib.request.urlopen', side_effect=err401):
        msg = send_voucher_sms(
            voucher=voucher,
            recipient_phone='0712345678',
            company=company
        )

        # Voucher status MUST remain AVAILABLE
        voucher.refresh_from_db()
        assert voucher.status == VoucherStatus.AVAILABLE
        assert msg.status == NotificationStatus.FAILED
