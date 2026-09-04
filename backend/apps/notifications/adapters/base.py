from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class SMSErrorCategory:
    PROVIDER_UNAVAILABLE = 'PROVIDER_UNAVAILABLE'
    TIMEOUT = 'TIMEOUT'
    TEMPORARY_PROVIDER_ERROR = 'TEMPORARY_PROVIDER_ERROR'
    INSUFFICIENT_BALANCE = 'INSUFFICIENT_BALANCE'
    INVALID_PHONE = 'INVALID_PHONE'
    AUTHENTICATION_FAILED = 'AUTHENTICATION_FAILED'
    INVALID_SENDER_ID = 'INVALID_SENDER_ID'
    PROVIDER_RATE_LIMIT = 'PROVIDER_RATE_LIMIT'
    INVALID_REQUEST = 'INVALID_REQUEST'
    UNHANDLED_ERROR = 'UNHANDLED_ERROR'


@dataclass
class NormalizedSMSResult:
    success: bool
    provider_reference: str = ''
    provider_status: str = ''
    delivery_status: str = ''
    failure_category: str = ''
    failure_code: str = ''
    failure_message: str = ''
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class NormalizedSenderID:
    sender_id: str
    external_id: str = ''
    display_name: str = ''
    status: str = 'active'
    is_active: bool = True
    raw_response: Optional[Dict[str, Any]] = None


class SMSProviderAdapter(ABC):
    """
    Abstract interface for multi-provider SMS delivery adapters.
    """

    @abstractmethod
    def send_message(
        self,
        recipient_phone: str,
        message_text: str,
        config: Any,
        sender_id: Optional[str] = None
    ) -> NormalizedSMSResult:
        """
        Send SMS message through provider using resolved sender ID.
        """
        pass

    @abstractmethod
    def validate_configuration(self, config: Any) -> bool:
        """
        Validate provider credentials and configuration structure.
        """
        pass

    def list_sender_ids(self, config: Any) -> List[NormalizedSenderID]:
        """
        Query available, provider-approved sender IDs for this provider configuration.
        """
        return []
