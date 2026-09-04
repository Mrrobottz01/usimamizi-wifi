# RafikiSMS Provider Integration & Sender ID Architecture

Comprehensive technical documentation for **RafikiSMS Gateway Adapter & Sender ID Architecture** in **Usimamizi Wi-Fi**.

## 1. Gateway Specifications

- **Provider:** RafikiSMS
- **Base URL:** `https://api.rafikisms.com`
- **Send Endpoint:** `POST /v1/vendor/send-sms`
- **Sender Names Endpoint:** `GET /v1/vendor/sender-names`
- **Delivery Webhook Endpoint:** `POST /api/v1/webhooks/sms/rafikisms/`
- **Authentication:** `X-API-Key: <API_KEY>` header

---

## 2. Security & Credential Storage

API keys must:
- Never be committed to source repositories.
- Never be logged in plain text.
- Never be returned to tenant frontends.
- Be stored in `encrypted_credentials` or environment configuration.

---

## 3. Phone Number Boundary

The canonical internal system representation is E.164 (`+255712345678`).
At the RafikiSMS adapter boundary, the leading `+` is removed (`255712345678`) to comply with API requirements without altering internal database records.

---

## 4. Sender ID Discovery & Synchronization

### Endpoint
`GET https://api.rafikisms.com/v1/vendor/sender-names`

### Provider Response Format
```json
{
  "success": true,
  "message": "Sender names retrieved successfully",
  "data": {
    "sender_names": [
      {
        "id": "c893d701-e1d8-4b00-8634-8c464e56ba11",
        "senderid": "STARSHINE",
        "sample_content": "This sender name is used for order confirmations",
        "status": "active",
        "created": "2025-07-08T14:07:56.000Z"
      }
    ]
  }
}
```

### Sync Service (`sync_provider_sender_ids`)
- Discovers upstream sender names and caches them in `SMSProviderSenderID`.
- Automatically marks missing senders as `is_available = False`.
- Automatically assigns the first active sender as `is_default = True` if none exists.
- Records `last_sender_sync_at` timestamp.

---

## 5. Hierarchical Provider-Specific Sender Resolution

Sender ID resolution order:
1. **Explicit preferred sender** (if valid for this provider).
2. **Tenant override** (`TenantSMSSenderPreference` if set and valid for this provider).
3. **Provider default synced sender ID** (`NotificationProviderConfiguration.default_sender_id`).
4. **First available synced sender** (`SMSProviderSenderID.is_available=True`).
5. **Configuration fallback** (`NotificationProviderConfiguration.sender_id`).

### Failover Decoupling
Sender IDs are provider-specific. If failover moves from Beem to RafikiSMS, `resolve_sender_id` re-evaluates the sender pool for RafikiSMS so Beem's sender ID is never passed to RafikiSMS.

---

## 6. Single SMS Send Payload & Response

### Request Example
```http
POST /v1/vendor/send-sms HTTP/1.1
Host: api.rafikisms.com
X-API-Key: sk_your_api_key_here
Content-Type: application/json

{
  "phone": "255712345678",
  "message": "Usimamizi Wi-Fi Voucher: K7PM-4XQ9",
  "sender_id": "STARSHINE"
}
```

### Success Response Example
```json
{
  "status": "success",
  "message": "SMS queued successfully",
  "data": {
    "message": "SMS has been queued for sending",
    "sms_log_id": 19725260,
    "note": "SMS will be processed asynchronously."
  }
}
```

---

## 7. Message Length Validation

RafikiSMS limits SMS content to **160 characters**.
Pre-transmission validation in `RafikiSMSAdapter` checks `len(message_text) <= 160`. If exceeded, `SMSErrorCategory.INVALID_REQUEST` (`MESSAGE_TOO_LONG`) is returned without transmitting an HTTP request.

---

## 8. Delivery Webhook & Idempotency

### Endpoint
`POST /api/v1/webhooks/sms/rafikisms/`

### Payload Example
```json
{
  "event": "sms.delivery_status",
  "event_time": "2026-08-30T10:00:00Z",
  "data": {
    "sms_log_id": 19725260,
    "status": "delivered",
    "recipient": "255712345678",
    "transaction_id": "19725260"
  }
}
```

### Idempotency & Transition Safety
- `data.sms_log_id` and `data.transaction_id` serve as idempotency keys.
- Duplicate callbacks return `HTTP 200 OK` in < 100ms without duplicating attempts or regressing status from `DELIVERED`.

---

## 9. Delivery Attempt Snapshotting

Every delivery attempt records a permanent snapshot on `NotificationDeliveryAttempt`:
- `provider_code`: e.g. `rafikisms`
- `sender_id`: e.g. `STARSHINE` (snapshot of the exact sender ID used)
- `provider_reference`: e.g. `19725260`
- `started_at`, `completed_at`
- `status`: `SUCCESS` / `FAILED`

A later change in default sender ID does **not** alter historical attempt snapshots.
