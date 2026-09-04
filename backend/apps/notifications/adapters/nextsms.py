import json
import urllib.error
import urllib.request
from typing import Any, Optional

from .base import NormalizedSMSResult, SMSErrorCategory, SMSProviderAdapter


class NextSMSTanzaniaAdapter(SMSProviderAdapter):
    """
    SMS Provider Adapter for NextSMS Tanzania (Messaging Service API V2).
    API Docs: https://documenter.getpostman.com/view/1679195/2sAYkDP1XN
    Endpoint: POST https://messaging-service.co.tz/api/sms/v2/text/single
    """

    def send_message(
        self,
        recipient_phone: str,
        message_text: str,
        config: Any,
        sender_id: Optional[str] = None
    ) -> NormalizedSMSResult:
        base_url = getattr(config, 'base_url', '') or 'https://messaging-service.co.tz/api/sms/v2/text/single'
        effective_sender_id = sender_id or getattr(config, 'sender_id', '') or 'Usimamizi'

        settings = getattr(config, 'settings_json', {}) or {}
        encrypted = getattr(config, 'encrypted_credentials', {}) or {}
        api_token = encrypted.get('api_token') or settings.get('api_token') or encrypted.get('access_token')

        if not api_token:
            return NormalizedSMSResult(
                success=False,
                failure_category=SMSErrorCategory.AUTHENTICATION_FAILED,
                failure_code='MISSING_CREDENTIALS',
                failure_message='NextSMS API token is missing.'
            )

        clean_phone = recipient_phone.replace('+', '').strip()

        payload = {
            "from": effective_sender_id,
            "to": clean_phone,
            "text": message_text
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_token}"
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

                messages = res_json.get('messages', [])
                if messages and len(messages) > 0:
                    first_msg = messages[0]
                    status_obj = first_msg.get('status', {})
                    msg_id = first_msg.get('messageId', '')

                    group_name = status_obj.get('groupName', '')
                    is_sent = group_name in ['PENDING', 'DELIVERY', 'SENT'] or status_obj.get('id') in [50, 51, 52, 73]

                    if is_sent:
                        return NormalizedSMSResult(
                            success=True,
                            provider_reference=msg_id,
                            provider_status=status_obj.get('name', 'SENT'),
                            delivery_status='SENT',
                            raw_response=res_json
                        )
                    else:
                        return NormalizedSMSResult(
                            success=False,
                            provider_reference=msg_id,
                            provider_status=status_obj.get('name', 'FAILED'),
                            failure_category=SMSErrorCategory.TEMPORARY_PROVIDER_ERROR,
                            failure_code=str(status_obj.get('id', '')),
                            failure_message=status_obj.get('description', 'NextSMS rejected message.'),
                            raw_response=res_json
                        )
                else:
                    return NormalizedSMSResult(
                        success=False,
                        failure_category=SMSErrorCategory.UNHANDLED_ERROR,
                        failure_code='NO_MESSAGES_RETURNED',
                        failure_message='NextSMS API returned no message elements.',
                        raw_response=res_json
                    )

        except urllib.error.HTTPError as err:
            err_body = err.read().decode('utf-8') if err.fp else ''
            try:
                err_json = json.loads(err_body)
            except Exception:
                err_json = {}

            category = SMSErrorCategory.TEMPORARY_PROVIDER_ERROR
            if err.code in [401, 403]:
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
        return bool(encrypted.get('api_token') or settings.get('api_token') or encrypted.get('access_token'))
