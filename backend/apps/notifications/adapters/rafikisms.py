import json
import urllib.error
import urllib.request
from typing import Any, List, Optional

from .base import NormalizedSenderID, NormalizedSMSResult, SMSErrorCategory, SMSProviderAdapter


class RafikiSMSAdapter(SMSProviderAdapter):
    """
    SMS Provider Adapter for RafikiSMS API.
    API Docs: https://developers.rafikisms.com/
    Endpoints:
      - Send SMS: POST https://api.rafikisms.com/v1/vendor/send-sms
      - Sender IDs: GET https://api.rafikisms.com/v1/vendor/sender-names
    """

    def send_message(
        self,
        recipient_phone: str,
        message_text: str,
        config: Any,
        sender_id: Optional[str] = None
    ) -> NormalizedSMSResult:
        # Pre-transmission length validation (max 160 characters per SMS)
        if len(message_text) > 160:
            return NormalizedSMSResult(
                success=False,
                failure_category=SMSErrorCategory.INVALID_REQUEST,
                failure_code='MESSAGE_TOO_LONG',
                failure_message=f'Message exceeds maximum length of 160 characters ({len(message_text)} chars).'
            )

        base_url = getattr(config, 'base_url', '') or 'https://api.rafikisms.com'
        base_url = base_url.rstrip('/')
        endpoint = f"{base_url}/v1/vendor/send-sms"

        # Resolved sender ID
        effective_sender_id = sender_id or getattr(config, 'sender_id', '') or 'USIMAMIZI'

        settings = getattr(config, 'settings_json', {}) or {}
        encrypted = getattr(config, 'encrypted_credentials', {}) or {}
        api_key = encrypted.get('api_key') or settings.get('api_key')

        if not api_key:
            return NormalizedSMSResult(
                success=False,
                failure_category=SMSErrorCategory.AUTHENTICATION_FAILED,
                failure_code='MISSING_CREDENTIALS',
                failure_message='RafikiSMS API key is missing.'
            )

        # Phone format transformation (+255712345678 -> 255712345678)
        clean_phone = recipient_phone.replace('+', '').strip()

        payload = {
            "phone": clean_phone,
            "message": message_text,
            "sender_id": effective_sender_id
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": api_key
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_body = resp.read().decode('utf-8')
                res_json = json.loads(resp_body)

                is_success = res_json.get('status') == 'success' or res_json.get('success') is True
                data_obj = res_json.get('data', {}) if isinstance(res_json.get('data'), dict) else {}

                ref_id = str(
                    data_obj.get('sms_log_id') or
                    data_obj.get('transaction_id') or
                    data_obj.get('message_id') or
                    data_obj.get('reference_id') or
                    res_json.get('message_id', '')
                )

                if is_success:
                    return NormalizedSMSResult(
                        success=True,
                        provider_reference=ref_id,
                        provider_status='QUEUED',
                        delivery_status='SENT',
                        raw_response=res_json
                    )
                else:
                    return NormalizedSMSResult(
                        success=False,
                        provider_reference=ref_id,
                        provider_status='FAILED',
                        failure_category=SMSErrorCategory.TEMPORARY_PROVIDER_ERROR,
                        failure_code=str(res_json.get('status', 'FAILED')),
                        failure_message=res_json.get('message', 'RafikiSMS request rejected.'),
                        raw_response=res_json
                    )

        except urllib.error.HTTPError as err:
            err_body = err.read().decode('utf-8') if err.fp else ''
            try:
                err_json = json.loads(err_body)
            except Exception:
                err_json = {}

            category = SMSErrorCategory.TEMPORARY_PROVIDER_ERROR
            if err.code in [400, 422]:
                category = SMSErrorCategory.INVALID_REQUEST
            elif err.code in [401, 403]:
                category = SMSErrorCategory.AUTHENTICATION_FAILED
            elif err.code == 429:
                category = SMSErrorCategory.PROVIDER_RATE_LIMIT

            return NormalizedSMSResult(
                success=False,
                failure_category=category,
                failure_code=str(err.code),
                failure_message=f"HTTP {err.code}: {err_json.get('message', err.reason)}",
                raw_response=err_json
            )
        except urllib.error.URLError as err:
            reason_str = str(err.reason)
            category = SMSErrorCategory.TIMEOUT if 'timed out' in reason_str.lower() else SMSErrorCategory.PROVIDER_UNAVAILABLE
            return NormalizedSMSResult(
                success=False,
                failure_category=category,
                failure_code='CONNECTION_ERROR',
                failure_message=reason_str
            )
        except Exception as err:
            return NormalizedSMSResult(
                success=False,
                failure_category=SMSErrorCategory.UNHANDLED_ERROR,
                failure_code='EXCEPTION',
                failure_message=str(err)
            )

    def validate_configuration(self, config: Any) -> bool:
        encrypted = getattr(config, 'encrypted_credentials', {}) or {}
        settings = getattr(config, 'settings_json', {}) or {}
        return bool(encrypted.get('api_key') or settings.get('api_key'))

    def list_sender_ids(self, config: Any) -> List[NormalizedSenderID]:
        """
        Query available sender IDs from RafikiSMS: GET /v1/vendor/sender-names
        """
        base_url = getattr(config, 'base_url', '') or 'https://api.rafikisms.com'
        base_url = base_url.rstrip('/')
        endpoint = f"{base_url}/v1/vendor/sender-names"

        settings = getattr(config, 'settings_json', {}) or {}
        encrypted = getattr(config, 'encrypted_credentials', {}) or {}
        api_key = encrypted.get('api_key') or settings.get('api_key')

        if not api_key:
            return []

        headers = {
            "Accept": "application/json",
            "X-API-Key": api_key
        }

        try:
            req = urllib.request.Request(endpoint, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_body = resp.read().decode('utf-8')
                res_json = json.loads(resp_body)

                data_obj = res_json.get('data', {}) if isinstance(res_json.get('data'), dict) else {}
                sender_names = data_obj.get('sender_names', []) if isinstance(data_obj.get('sender_names'), list) else []

                results = []
                for item in sender_names:
                    if not isinstance(item, dict):
                        continue
                    sid = item.get('senderid') or item.get('sender_id') or item.get('name')
                    if sid:
                        raw_status = str(item.get('status', 'active')).lower()
                        results.append(NormalizedSenderID(
                            sender_id=str(sid).strip(),
                            external_id=str(item.get('id', '')),
                            display_name=str(sid).strip(),
                            status=raw_status,
                            is_active=raw_status == 'active',
                            raw_response=item
                        ))
                return results
        except Exception:
            return []
