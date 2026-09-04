# Notifications Architecture Specification

**System Name:** Usimamizi Wi-Fi  
**Domain App:** `apps.notifications`  

---

## 1. Overview & Objectives

The notification domain is responsible for delivering Wi-Fi access vouchers, payment confirmation receipts, expiry reminders, and system alerts to Wi-Fi customers and tenant operators.

Because SMS delivery costs money and uses third-party gateways (e.g. Infobip, Twilio, NextSMS, Beem), the architecture strictly decouples provider implementations from core SaaS business logic.

---

## 2. Decoupled SMS Adapter Model

All SMS provider interactions implement the `SMSProviderAdapter` interface defined in `apps.notifications.adapters.base`:

```python
class SMSProviderAdapter(ABC):
    @abstractmethod
    def send_sms(self, *, recipient: str, message_body: str, sender_id: Optional[str] = None) -> SMSDeliveryResult:
        pass
```

---

## 3. Platform Credentials vs Tenant Preferences

- **Platform-Level Credentials:** Live API keys, HTTP endpoints, and provider tokens reside strictly in secure backend environment variables or encrypted platform config. They are NEVER exposed to tenant users or returned via frontend APIs.
- **Tenant-Level Preferences:** Tenant companies configure display parameters in `NotificationProviderConfiguration` (e.g. `sender_id`, default language, enabled message triggers, custom voucher message templates).

---

## 4. Message Lifecycle States

Notification messages progress through explicit status transitions:

```text
QUEUED  →  SENDING  →  SENT  /  DELIVERED
                        ↓
                     FAILED
```

- `QUEUED`: Message created by business event (e.g. voucher generation).
- `SENDING`: Worker claimed message for dispatch.
- `SENT`: Gateway acknowledged receipt with provider reference ID.
- `DELIVERED`: Final webhook delivery receipt confirmed.
- `FAILED`: Dispatch failed due to invalid number, network failure, or provider error.

---

## 5. Failure Isolation & Retry Behavior

- **Asynchronous Execution:** Notifications run asynchronously in background Celery tasks (`process_notification_task`).
- **Transaction Safety:** Failure to send an SMS notification MUST NEVER roll back an authorized payment or valid entitlement.
- **Retry Policy:** Celery tasks employ exponential backoff retries (max 3 retries) with state recorded in `NotificationMessage.attempts`.
