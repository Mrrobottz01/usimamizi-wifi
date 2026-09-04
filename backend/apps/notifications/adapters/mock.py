from typing import Any, List, Optional

from .base import NormalizedSenderID, NormalizedSMSResult, SMSProviderAdapter


class MockSMSProviderAdapter(SMSProviderAdapter):
    """
    Mock SMS Adapter for development & unit testing.
    """

    def send_message(
        self,
        recipient_phone: str,
        message_text: str,
        config: Any,
        sender_id: Optional[str] = None
    ) -> NormalizedSMSResult:
        cfg_code = getattr(config, 'code', '') if config else ''
        if 'fail_test' in recipient_phone or cfg_code == 'mock_primary':
            return NormalizedSMSResult(
                success=False,
                failure_category='TEMPORARY_PROVIDER_ERROR',
                failure_code='MOCK_FAIL',
                failure_message='Mock SMS failure requested.'
            )

        return NormalizedSMSResult(
            success=True,
            provider_reference='MOCK-MSG-12345',
            provider_status='SENT',
            delivery_status='SENT',
            raw_response={'status': 'mock_sent', 'recipient': recipient_phone, 'sender_id': sender_id}
        )

    def validate_configuration(self, config: Any) -> bool:
        return True

    def list_sender_ids(self, config: Any) -> List[NormalizedSenderID]:
        return [
            NormalizedSenderID(sender_id='USIMAMIZI', display_name='USIMAMIZI', status='active', is_active=True),
            NormalizedSenderID(sender_id='MYWIFI', display_name='MYWIFI', status='active', is_active=True),
        ]
