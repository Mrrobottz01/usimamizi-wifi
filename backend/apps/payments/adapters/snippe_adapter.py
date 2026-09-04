import hashlib
import hmac
import json
import logging
import re
import time
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any, Dict, Optional

from apps.payments.adapters.base import (
    PaymentInitiationResult,
    PaymentProviderAdapter,
    PaymentStatusResult,
)
from apps.payments.models import PaymentStatus

logger = logging.getLogger(__name__)


def normalize_tanzanian_phone(phone: str) -> str:
    """
    Normalize Tanzanian phone number to E.164 format (+255XXXXXXXXX).
    Supports:
      - 07XXXXXXXX -> +2557XXXXXXXX
      - 06XXXXXXXX -> +2556XXXXXXXX
      - 255XXXXXXXXX -> +255XXXXXXXXX
      - +255XXXXXXXXX -> +255XXXXXXXXX
      - 7XXXXXXXX / 6XXXXXXXX -> +255XXXXXXXXX
    """
    clean = re.sub(r'[\s\-\(\)]', '', phone.strip())

    if clean.startswith('+'):
        clean = clean[1:]

    if clean.startswith('0'):
        clean = '255' + clean[1:]
    elif not clean.startswith('255'):
        clean = '255' + clean

    if not re.match(r'^255[67]\d{8}$', clean):
        raise ValueError(f"Invalid Tanzanian mobile phone number: {phone}")

    return f"+{clean}"


def to_snippe_phone_format(e164_phone: str) -> str:
    """Strip leading '+' for Snippe API request payload (e.g. '255712345678')."""
    return e164_phone.lstrip('+')


class SnippePaymentAdapter(PaymentProviderAdapter):
    """
    Official Snippe Mobile Money payment provider integration.
    API Base: https://api.snippe.sh
    """

    def __init__(
        self,
        *,
        api_key: str,
        webhook_secret: Optional[str] = None,
        api_base_url: str = 'https://api.snippe.sh',
        timeout: int = 20
    ):
        self.api_key = api_key
        self.webhook_secret = webhook_secret or ''
        self.api_base_url = api_base_url.rstrip('/')
        self.timeout = timeout

    def create_payment(
        self,
        *,
        amount: Decimal,
        currency: str,
        phone_number: str,
        internal_reference: str,
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None
    ) -> PaymentInitiationResult:
        """
        Initiate direct mobile money collection via Snippe POST /v1/payments.
        Enforces Snippe idempotency key constraint: <= 30 characters.
        """
        # Ensure Idempotency-Key <= 30 chars
        safe_idempotency_key = idempotency_key[:30]

        normalized_phone = normalize_tanzanian_phone(phone_number)
        snippe_phone = to_snippe_phone_format(normalized_phone)

        # Snippe expects integer or standard amount string
        amount_int = int(amount) if amount == int(amount) else float(amount)

        payload: Dict[str, Any] = {
            "payment_type": "mobile",
            "details": {
                "amount": amount_int,
                "currency": currency or "TZS",
            },
            "amount": amount_int,
            "currency": currency or "TZS",
            "phone_number": snippe_phone,
            "customer": {
                "firstname": "WiFi",
                "lastname": "Customer",
                "email": f"{snippe_phone}@guest.usimamizi.wifi",
                "phone": snippe_phone,
            },
            "reference": internal_reference,
            "metadata": metadata or {},
        }
        if webhook_url:
            payload["webhook_url"] = webhook_url

        endpoint = f"{self.api_base_url}/v1/payments"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": safe_idempotency_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Usimamizi-WiFi/1.0",
        }

        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(endpoint, data=req_data, headers=headers, method='POST')

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                resp_bytes = response.read()
                resp_data = json.loads(resp_bytes.decode('utf-8'))

                data_obj = resp_data.get('data') if isinstance(resp_data.get('data'), dict) else resp_data
                provider_ref = data_obj.get('reference') or data_obj.get('id') or resp_data.get('reference') or resp_data.get('id') or ''
                checkout_url = data_obj.get('checkout_url') or resp_data.get('checkout_url') or ''
                payment_link_url = data_obj.get('payment_link') or resp_data.get('payment_link') or ''

                return PaymentInitiationResult(
                    success=True,
                    status=PaymentStatus.PENDING,
                    provider_reference=str(provider_ref),
                    checkout_url=checkout_url,
                    payment_link_url=payment_link_url,
                    raw_response=resp_data
                )

        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            logger.error("Snippe API HTTP %d error: %s", e.code, err_body)
            try:
                err_json = json.loads(err_body)
                err_msg = err_json.get('message') or err_json.get('error', {}).get('message') or str(err_json)
            except Exception:
                err_msg = f"HTTP {e.code}: {err_body}"

            return PaymentInitiationResult(
                success=False,
                status=PaymentStatus.FAILED,
                provider_reference="",
                raw_response={"http_status": e.code, "body": err_body},
                error_message=err_msg
            )
        except Exception as e:
            logger.exception("Unexpected error calling Snippe API: %s", e)
            return PaymentInitiationResult(
                success=False,
                status=PaymentStatus.FAILED,
                provider_reference="",
                error_message=str(e)
            )

    def get_payment_status(self, provider_reference: str) -> PaymentStatusResult:
        """
        Query current payment status from Snippe GET /v1/payments/{reference}.
        """
        endpoint = f"{self.api_base_url}/v1/payments/{provider_reference}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "Usimamizi-WiFi/1.0"
        }

        try:
            req = urllib.request.Request(endpoint, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                resp_bytes = response.read()
                resp_data = json.loads(resp_bytes.decode('utf-8'))

                data_node = resp_data.get('data') or resp_data
                remote_status = (data_node.get('status') or '').lower()

                if remote_status in ['completed', 'successful', 'success', 'paid']:
                    local_status = PaymentStatus.COMPLETED
                elif remote_status in ['failed', 'rejected', 'error']:
                    local_status = PaymentStatus.FAILED
                elif remote_status in ['expired', 'timedout']:
                    local_status = PaymentStatus.EXPIRED
                elif remote_status in ['cancelled', 'voided']:
                    local_status = PaymentStatus.CANCELLED
                else:
                    local_status = PaymentStatus.PENDING

                raw_amt = data_node.get('amount')
                if isinstance(raw_amt, dict):
                    amount_val = raw_amt.get('value')
                    currency = raw_amt.get('currency') or data_node.get('currency')
                else:
                    amount_val = raw_amt
                    currency = data_node.get('currency')

                amount = Decimal(str(amount_val)) if amount_val is not None else None

                return PaymentStatusResult(
                    status=local_status,
                    provider_reference=provider_reference,
                    amount=amount,
                    currency=currency,
                    paid_at=data_node.get('paid_at') or data_node.get('completed_at'),
                    raw_response=resp_data
                )
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            return PaymentStatusResult(
                status=PaymentStatus.PENDING,
                provider_reference=provider_reference,
                error_message=f"HTTP {e.code}: {err_body}"
            )
        except Exception as e:
            return PaymentStatusResult(
                status=PaymentStatus.PENDING,
                provider_reference=provider_reference,
                error_message=str(e)
            )

    def verify_webhook_signature(
        self,
        *,
        raw_payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
        tolerance_seconds: int = 300
    ) -> bool:
        """
        Verify incoming webhook HMAC-SHA256 signature using constant-time comparison.
        Prevents timing attacks and timestamp replay.
        """
        if not self.webhook_secret or not signature:
            return False

        # Verify timestamp freshness if provided
        if timestamp:
            try:
                ts_int = int(timestamp)
                now_int = int(time.time())
                if abs(now_int - ts_int) > tolerance_seconds:
                    logger.warning("Snippe webhook rejected: timestamp %d expired (current %d)", ts_int, now_int)
                    return False
            except (ValueError, TypeError):
                logger.warning("Snippe webhook rejected: invalid timestamp header %s", timestamp)
                return False

        secret_bytes = self.webhook_secret.encode('utf-8')

        # Mode 1: HMAC over timestamp + "." + raw_payload (standard RFC / Stripe style)
        if timestamp:
            to_sign_ts = timestamp.encode('utf-8') + b'.' + raw_payload
            expected_hmac_ts = hmac.new(secret_bytes, to_sign_ts, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected_hmac_ts.lower(), signature.lower()):
                return True

        # Mode 2: Direct HMAC over raw_payload
        expected_hmac_direct = hmac.new(secret_bytes, raw_payload, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected_hmac_direct.lower(), signature.lower()):
            return True

        return False
