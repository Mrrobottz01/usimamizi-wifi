import hashlib
import hmac
import json
import time
import urllib.error
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.payments.adapters.snippe_adapter import (
    SnippePaymentAdapter,
    normalize_tanzanian_phone,
    to_snippe_phone_format,
)
from apps.payments.models import PaymentStatus


def test_normalize_tanzanian_phone():
    # Local format
    assert normalize_tanzanian_phone('0712345678') == '+255712345678'
    assert normalize_tanzanian_phone('0687654321') == '+255687654321'

    # E.164 without plus
    assert normalize_tanzanian_phone('255712345678') == '+255712345678'

    # E.164 with plus
    assert normalize_tanzanian_phone('+255712345678') == '+255712345678'

    # Formatted with spaces / dashes
    assert normalize_tanzanian_phone('+255 712-345 678') == '+255712345678'

    # Invalid formats
    with pytest.raises(ValueError):
        normalize_tanzanian_phone('0812345678')

    with pytest.raises(ValueError):
        normalize_tanzanian_phone('12345')

    with pytest.raises(ValueError):
        normalize_tanzanian_phone('254712345678')  # Kenya


def test_to_snippe_phone_format():
    assert to_snippe_phone_format('+255712345678') == '255712345678'


def test_webhook_signature_verification():
    secret = 'whsec_test_secret_key_12345'
    adapter = SnippePaymentAdapter(api_key='test_key', webhook_secret=secret)

    raw_payload = b'{"event":"payment.completed","data":{"id":"pay_123"}}'
    current_time = str(int(time.time()))

    # Mode 1: Timestamped HMAC
    to_sign_ts = current_time.encode('utf-8') + b'.' + raw_payload
    valid_sig_ts = hmac.new(secret.encode('utf-8'), to_sign_ts, hashlib.sha256).hexdigest()

    assert adapter.verify_webhook_signature(
        raw_payload=raw_payload,
        signature=valid_sig_ts,
        timestamp=current_time
    ) is True

    # Mode 2: Direct HMAC
    valid_sig_direct = hmac.new(secret.encode('utf-8'), raw_payload, hashlib.sha256).hexdigest()
    assert adapter.verify_webhook_signature(
        raw_payload=raw_payload,
        signature=valid_sig_direct
    ) is True

    # Invalid signature
    assert adapter.verify_webhook_signature(
        raw_payload=raw_payload,
        signature='invalid_hex_signature_abcdef',
        timestamp=current_time
    ) is False

    # Expired timestamp (> 300 seconds)
    expired_time = str(int(time.time()) - 600)
    to_sign_expired = expired_time.encode('utf-8') + b'.' + raw_payload
    sig_expired = hmac.new(secret.encode('utf-8'), to_sign_expired, hashlib.sha256).hexdigest()
    assert adapter.verify_webhook_signature(
        raw_payload=raw_payload,
        signature=sig_expired,
        timestamp=expired_time
    ) is False


@patch('urllib.request.urlopen')
def test_create_payment_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "status": "success",
        "data": {
            "id": "pay_snippe_9988",
            "checkout_url": "https://checkout.snippe.sh/pay_9988",
            "payment_link": "https://snippe.me/p9988"
        }
    }).encode('utf-8')
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = SnippePaymentAdapter(api_key='test_api_key')
    res = adapter.create_payment(
        amount=Decimal('1000.00'),
        currency='TZS',
        phone_number='+255712345678',
        internal_reference='TXN-20260903-ABCD',
        idempotency_key='very_long_idempotency_key_that_exceeds_30_chars_12345'
    )

    assert res.success is True
    assert res.status == PaymentStatus.PENDING
    assert res.provider_reference == 'pay_snippe_9988'
    assert res.checkout_url == 'https://checkout.snippe.sh/pay_9988'


@patch('urllib.request.urlopen')
def test_create_payment_error_handling(mock_urlopen):
    err = urllib.error.HTTPError(
        url='https://api.snippe.sh/v1/payments',
        code=400,
        msg='Bad Request',
        hdrs={},
        fp=MagicMock(read=lambda: b'{"error":{"message":"Invalid phone number"}}')
    )
    mock_urlopen.side_effect = err

    adapter = SnippePaymentAdapter(api_key='test_api_key')
    res = adapter.create_payment(
        amount=Decimal('2000.00'),
        currency='TZS',
        phone_number='+255712345678',
        internal_reference='TXN-20260903-ERR',
        idempotency_key='idmp_test_123'
    )

    assert res.success is False
    assert res.status == PaymentStatus.FAILED
    assert 'Invalid phone number' in res.error_message
