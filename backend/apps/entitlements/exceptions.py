class EntitlementError(Exception):
    """Base exception for Access Entitlement domain errors."""
    pass


class InvalidEntitlementStateTransition(EntitlementError):
    """Raised when an entitlement lifecycle transition is invalid."""
    pass


class EntitlementQuotaExhausted(EntitlementError):
    """Raised when data or usage-time quota is exhausted."""
    pass


class EntitlementAuthorizationDenied(EntitlementError):
    """Raised when entitlement authorization is rejected."""
    def __init__(self, reason: str, message: str = ''):
        self.reason = reason
        self.message = message or f"Entitlement authorization denied: {reason}"
        super().__init__(self.message)
