import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.companies.services.company_services import create_company
from apps.notifications.adapters.base import NormalizedSenderID
from apps.notifications.adapters.rafikisms import RafikiSMSAdapter
from apps.notifications.models import (
    NotificationMessage,
    NotificationProviderConfiguration,
    NotificationStatus,
    SMSProviderSenderID,
    SMSProviderType,
    TenantSMSSenderPreference,
)
from apps.notifications.services.sms_services import (
    resolve_sender_id,
    route_and_send_sms,
    sync_provider_sender_ids,
)

User = get_user_model()


class DummyConfig:
    def __init__(self, api_key='sk_test_12345', base_url='https://api.rafikisms.com', sender_id='USIMAMIZI'):
        self.code = 'rafikisms'
        self.base_url = base_url
        self.sender_id = sender_id
        self.encrypted_credentials = {'api_key': api_key}
        self.settings_json = {}


def test_rafikisms_list_sender_ids_from_api():
    adapter = RafikiSMSAdapter()
    config = DummyConfig()

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "success": True,
        "message": "Sender names retrieved successfully",
        "data": {
            "sender_names": [
                {
                    "id": "c893d701-e1d8-4b00-8634-8c464e56ba11",
                    "senderid": "STARSHINE",
                    "sample_content": "Order confirmations",
                    "status": "active",
                    "created": "2025-07-08T14:07:56.000Z"
                },
                {
                    "id": "24e1ffaf-e399-4b15-983a-53539e4970bd",
                    "senderid": "MYBRAND",
                    "sample_content": "Marketing alerts",
                    "status": "pending",
                    "created": "2025-07-08T14:07:56.000Z"
                }
            ]
        }
    }).encode('utf-8')
    mock_response.__enter__.return_value = mock_response

    with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
        senders = adapter.list_sender_ids(config)

        assert len(senders) == 2
        assert senders[0].sender_id == 'STARSHINE'
        assert senders[0].status == 'active'
        assert senders[0].is_active is True
        assert senders[1].sender_id == 'MYBRAND'
        assert senders[1].status == 'pending'
        assert senders[1].is_active is False

        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.get_full_url() == 'https://api.rafikisms.com/v1/vendor/sender-names'
        assert req_arg.headers.get('X-api-key') == 'sk_test_12345' or req_arg.headers.get('X-API-Key') == 'sk_test_12345'


@pytest.mark.django_db
def test_sync_provider_sender_ids_and_vanishing():
    config = NotificationProviderConfiguration.objects.create(
        name='RafikiSMS',
        code='rafikisms',
        provider_type=SMSProviderType.RAFIKISMS,
        priority=1,
        is_active=True,
        encrypted_credentials={'api_key': 'sk_test'}
    )

    # Initial old sender in DB
    SMSProviderSenderID.objects.create(
        provider_configuration=config,
        sender_id='OLD_SENDER',
        status='active',
        is_available=True
    )

    mock_senders = [
        NormalizedSenderID(sender_id='USIMAMIZI', display_name='USIMAMIZI', status='active', is_active=True),
        NormalizedSenderID(sender_id='HOTELNET', display_name='HOTELNET', status='active', is_active=True),
    ]

    with patch.object(RafikiSMSAdapter, 'list_sender_ids', return_value=mock_senders):
        synced = sync_provider_sender_ids(provider_config=config)

        assert len(synced) == 3  # 2 active + 1 marked unavailable
        assert SMSProviderSenderID.objects.filter(provider_configuration=config, sender_id='USIMAMIZI', is_available=True).exists()
        assert SMSProviderSenderID.objects.filter(provider_configuration=config, sender_id='HOTELNET', is_available=True).exists()

        old = SMSProviderSenderID.objects.get(provider_configuration=config, sender_id='OLD_SENDER')
        assert old.is_available is False  # Marked unavailable!

        config.refresh_from_db()
        assert config.last_sender_sync_at is not None
        assert config.default_sender_id in ['USIMAMIZI', 'HOTELNET']


@pytest.mark.django_db
def test_resolve_sender_id_hierarchy():
    user = User.objects.create_user(email='sender_user@example.com', password='Password123!')
    company = create_company(name='Sender Co', user=user)

    config = NotificationProviderConfiguration.objects.create(
        name='RafikiSMS',
        code='rafikisms',
        provider_type=SMSProviderType.RAFIKISMS,
        priority=1,
        is_active=True,
        default_sender_id='DEFAULT_SENDER'
    )

    SMSProviderSenderID.objects.create(provider_configuration=config, sender_id='DEFAULT_SENDER', is_available=True, is_default=True)
    SMSProviderSenderID.objects.create(provider_configuration=config, sender_id='TENANT_SENDER', is_available=True)
    SMSProviderSenderID.objects.create(provider_configuration=config, sender_id='PREFERRED_SENDER', is_available=True)

    # 1. Fallback to default
    resolved = resolve_sender_id(company=company, provider_config=config)
    assert resolved == 'DEFAULT_SENDER'

    # 2. Tenant override
    TenantSMSSenderPreference.objects.create(company=company, provider_code='rafikisms', sender_id='TENANT_SENDER')
    resolved = resolve_sender_id(company=company, provider_config=config)
    assert resolved == 'TENANT_SENDER'

    # 3. Explicit preferred sender
    resolved = resolve_sender_id(company=company, provider_config=config, preferred_sender='PREFERRED_SENDER')
    assert resolved == 'PREFERRED_SENDER'


@pytest.mark.django_db
def test_sender_id_failover_provider_specific_and_snapshot_immutability():
    user = User.objects.create_user(email='failover_sender@example.com', password='Password123!')
    company = create_company(name='Failover Sender Co', user=user)

    # Provider 1: Beem (Default sender: BEEM_SENDER, fails)
    cfg1 = NotificationProviderConfiguration.objects.create(
        company=company,
        name='Beem Primary',
        code='beem_p1',
        provider_type=SMSProviderType.BEEM,
        priority=1,
        is_active=True,
        default_sender_id='BEEM_SENDER',
        encrypted_credentials={'api_key': 'key', 'secret_key': 'sec'}
    )
    SMSProviderSenderID.objects.create(provider_configuration=cfg1, sender_id='BEEM_SENDER', is_available=True, is_default=True)

    # Provider 2: RafikiSMS (Default sender: RAFIKI_SENDER, succeeds)
    cfg2 = NotificationProviderConfiguration.objects.create(
        company=company,
        name='Rafiki Secondary',
        code='rafikisms_p2',
        provider_type=SMSProviderType.RAFIKISMS,
        priority=2,
        is_active=True,
        default_sender_id='RAFIKI_SENDER',
        encrypted_credentials={'api_key': 'key'}
    )
    SMSProviderSenderID.objects.create(provider_configuration=cfg2, sender_id='RAFIKI_SENDER', is_available=True, is_default=True)

    msg = NotificationMessage.objects.create(
        company=company,
        channel='SMS',
        recipient='+255712345678',
        phone_normalized='+255712345678',
        rendered_content='Voucher: K7PM-4XQ9',
        status=NotificationStatus.QUEUED
    )

    # Mock Beem failure and RafikiSMS success
    mock_beem_fail = MagicMock()
    mock_beem_fail.read.return_value = json.dumps({"code": 105, "message": "Insufficient Balance"}).encode('utf-8')
    mock_beem_fail.__enter__.return_value = mock_beem_fail

    mock_rafiki_success = MagicMock()
    mock_rafiki_success.read.return_value = json.dumps({
        "status": "success",
        "data": {"sms_log_id": 998877}
    }).encode('utf-8')
    mock_rafiki_success.__enter__.return_value = mock_rafiki_success

    with patch('urllib.request.urlopen', side_effect=[mock_beem_fail, mock_rafiki_success]):
        processed = route_and_send_sms(notification_message=msg)
        assert processed.status == NotificationStatus.SENT

        attempts = list(processed.attempts.all())
        assert len(attempts) == 2

        # Verify Attempt 1 snapshotted BEEM_SENDER
        assert attempts[0].provider_code == 'beem_p1'
        assert attempts[0].sender_id == 'BEEM_SENDER'
        assert attempts[0].status == 'FAILED'

        # Verify Attempt 2 snapshotted RAFIKI_SENDER (NOT Beem's sender!)
        assert attempts[1].provider_code == 'rafikisms_p2'
        assert attempts[1].sender_id == 'RAFIKI_SENDER'
        assert attempts[1].status == 'SUCCESS'

    # Immutability check: Changing default sender on config later does NOT alter historical attempt
    cfg2.default_sender_id = 'NEW_BRAND_2027'
    cfg2.save()

    attempts[1].refresh_from_db()
    assert attempts[1].sender_id == 'RAFIKI_SENDER'


@pytest.mark.django_db
def test_sender_id_api_endpoints():
    user = User.objects.create_user(email='api_sender_user@example.com', password='Password123!')
    company = create_company(name='API Sender Co', user=user)

    config = NotificationProviderConfiguration.objects.create(
        name='RafikiSMS',
        code='rafikisms',
        provider_type=SMSProviderType.RAFIKISMS,
        priority=1,
        is_active=True,
        encrypted_credentials={'api_key': 'sk_test'}
    )

    client = APIClient()
    client.force_authenticate(user=user)

    mock_senders = [
        NormalizedSenderID(sender_id='SENDER_1', display_name='SENDER_1', status='active', is_active=True),
        NormalizedSenderID(sender_id='SENDER_2', display_name='SENDER_2', status='active', is_active=True),
    ]

    with patch.object(RafikiSMSAdapter, 'list_sender_ids', return_value=mock_senders):
        # 1. Sync sender IDs
        sync_res = client.post(
            f'/api/v1/settings/notifications/sms/providers/{config.id}/sync-sender-ids/',
            data={'company_id': str(company.id)},
            format='json'
        )
        assert sync_res.status_code == 200
        assert len(sync_res.data['sender_ids']) == 2

        # 2. Get sender IDs list
        list_res = client.get(
            f'/api/v1/settings/notifications/sms/providers/{config.id}/sender-ids/?company_id={company.id}'
        )
        assert list_res.status_code == 200
        assert len(list_res.data) == 2

        # 3. Set default sender ID
        patch_res = client.patch(
            f'/api/v1/settings/notifications/sms/providers/{config.id}/default-sender/',
            data={'company_id': str(company.id), 'sender_id': 'SENDER_2'},
            format='json'
        )
        assert patch_res.status_code == 200
        config.refresh_from_db()
        assert config.default_sender_id == 'SENDER_2'
