from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass
class PaymentInitiationResult:
    success: bool
    status: str  # PaymentStatus enum value
    provider_reference: str
    checkout_url: str = ''
    payment_link_url: str = ''
    raw_response: Optional[Dict[str, Any]] = None
    error_message: str = ''


@dataclass
class PaymentStatusResult:
    status: str  # PaymentStatus enum value
    provider_reference: str
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    paid_at: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    error_message: str = ''


class PaymentProviderAdapter(ABC):
    """
    Abstract adapter for payment gateways (e.g. Snippe, Selcom, Pesapal).
    """

    @abstractmethod
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
        Initiate direct mobile money collection or hosted checkout.
        """
        pass

    @abstractmethod
    def get_payment_status(self, provider_reference: str) -> PaymentStatusResult:
        """
        Query current payment status from the provider.
        """
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        *,
        raw_payload: bytes,
        signature: str,
        timestamp: Optional[str] = None
    ) -> bool:
        """
        Verify incoming webhook cryptographic signature.
        """
        pass
