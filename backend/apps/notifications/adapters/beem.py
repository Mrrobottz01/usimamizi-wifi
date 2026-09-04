import base64
import json
import urllib.error
import urllib.request
from typing import Any, Optional

from .base import NormalizedSMSResult, SMSErrorCategory, SMSProviderAdapter


class BeemAfricaSMSAdapter(SMSProviderAdapter):
    """
    SMS Provider Adapter for Beem Africa SMS API.
    API Docs: https://docs.beem.africa/
    Endpoint: POST https://api.beem.africa/v1/send-sms
    """

    def send_message(
        self,
        recipient_phone: str,
        message_text: str,
        config: Any,
        sender_id: Optional[str] = None
    ) -> NormalizedSMSResult:
        base_url = getattr(config, 'base_url', '') or 'https://api.beem.africa/v1/send-sms'
        effective_sender_id = sender_id or getattr(config, 'sender_id', '') or 'Usimamizi'

        # Extract credentials
        settings = getattr(config, 'settings_json', {}) or {}
        encrypted = getattr(config, 'encrypted_credentials', {}) or {}
        api_key = encrypted.get('api_key') or settings.get('api_key', '')
        secret_key = encrypted.get('secret_key') or settings.get('secret_key', '')

        if not api_key or not secret_key:
            return NormalizedSMSResult(
                success=False,
                failure_category=SMSErrorCategory.AUTHENTICATION_FAILED,
                failure_code='MISSING_CREDENTIALS',
                failure_message='Beem Africa API key or secret key is missing.'
            )

        clean_phone = recipient_phone.replace('+', '').strip()

        payload = {
            "source_addr": effective_sender_id,
            "encoding": 0,
            "schedule_time": "",
            "message": message_text,
            "recipients": [
                {
                    "recipient_id": 1,
                    "dest_addr": clean_phone
                }
            ]
        }

        # Basic Auth header
        credentials_str = f"{api_key}:{secret_key}"
        encoded_auth = base64.b64encode(credentials_str.encode('utf-8')).decode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

        try:
            req = urllib.request.Request(
                base_url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_body = resp.read().decode('utf-8')
                res_json = json.loads(resp_body)

                is_successful = res_json.get('successful') is True or res_json.get('code') == 100
                req_id = str(res_json.get('request_id', ''))

                if is_successful:
                    return NormalizedSMSResult(
                        success=True,
                        provider_reference=req_id,
                        provider_status='SENT',
                        delivery_status='SENT',
                        raw_response=res_json
                    )
                else:
                    return NormalizedSMSResult(
                        success=False,
                        provider_reference=req_id,
                        provider_status='FAILED',
                        failure_category=SMSErrorCategory.TEMPORARY_PROVIDER_ERROR,
                        failure_code=str(res_json.get('code', '')),
                        failure_message=res_json.get('message', 'Beem Africa request rejected.'),
                        raw_response=res_json
                    )

        except urllib.error.HTTPError as err:
            err_body = err.read().decode('utf-8') if err.fp else ''
            try:
                err_json = json.loads(err_body)
            except Exception:
                err_json = {}

            category = SMSErrorCategory.TEMPORARY_PROVIDER_ERROR
            if err.code == 401 or err.code == 403:
                category = SMSErrorCategory.AUTHENTICATION_FAILED
            elif err.code == 400:
                category = SMSErrorCategory.INVALID_PHONE

            return NormalizedSMSResult(
                success=False,
                failure_category=category,
                failure_code=str(err.code),
                failure_message=f"HTTP {err.code}: {err_json.get('message', err.reason)}",
                raw_response=err_json
            )
        except urllib.error.URLError as err:
            return NormalizedSMSResult(
                success=False,
                failure_category=SMSErrorCategory.PROVIDER_UNAVAILABLE,
                failure_code='CONNECTION_ERROR',
                failure_message=str(err.reason)
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
