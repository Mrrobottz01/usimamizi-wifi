# SMS History & Delivery Logs Module Specification

Comprehensive technical documentation for the **SMS History & Delivery Logs** module in **Usimamizi Wi-Fi** (Phase 2 Operational Extension).

---

## 1. Overview & Data Model

The module exposes operational SMS notification logs safely to tenant operators with multi-provider failover tracking, delivery receipt timeline, phone number privacy masking, and safe retry controls.

### Data Relationships
```text
NotificationMessage (1) ──── (N) NotificationDeliveryAttempt
        │
        └── (optional FK) ────> Voucher (1) ────> VoucherBatch ────> Plan
```

### Models Involved
- `NotificationMessage`: Logical SMS record (`id`, `company`, `channel`, `recipient`, `phone_normalized`, `template`, `voucher`, `rendered_content`, `status`, timestamps).
- `NotificationDeliveryAttempt`: Individual provider attempts (`attempt_number`, `provider_code`, `sender_id`, `provider_reference`, `provider_status`, `status`, `failure_category`, `failure_code`, `failure_reason`, timestamps).
- `Voucher`: Linked voucher entity for automated voucher SMS delivery (`display_code`, `plan`, `batch`).

---

## 2. API Endpoints

### 1. Paginated SMS History List
`GET /api/v1/notifications/sms/history/?company_id={uuid}`

#### Query Parameters
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)
- `status`: Filter by `QUEUED`, `SENDING`, `SENT`, `DELIVERED`, `FAILED`
- `failed_only`: Boolean (`true`) to filter failed messages only
- `delivered_only`: Boolean (`true`) to filter delivered messages only
- `provider`: Filter by provider code (`rafikisms`, `beem`, `nextsms`)
- `sender_id`: Filter by sender ID string
- `date_from`, `date_to`: ISO date range filters
- `search`: Full text search on recipient, normalized phone, provider reference, voucher code, or content
- `sort_by`: Sorting field (default: `-created_at`, supports `created_at`, `sent_at`, `delivered_at`, `status`)

#### Response Example
```json
{
  "results": [
    {
      "id": "4eb601cf-92a4-4676-9e1c-48af96d329ca",
      "recipient_masked": "+25575****012",
      "recipient": "0757047012",
      "phone_normalized": "+255757047012",
      "channel": "SMS",
      "message_type": "VOUCHER_SMS",
      "status": "DELIVERED",
      "provider_used": "rafikisms",
      "sender_id": "KOLOI TECH",
      "attempt_count": 2,
      "provider_reference": "19882233",
      "voucher_id": "84824d55-89f5-4422-9214-411a7e2b7e12",
      "voucher_code": "R2WS-VXSS",
      "voucher_batch_id": "183141f1-39e2-4db1-9c60-318e878593a2",
      "plan_name": "1 Hour High Speed",
      "created_at": "2026-08-30T10:10:17Z",
      "sent_at": "2026-08-30T10:10:18Z",
      "delivered_at": "2026-08-30T10:10:22Z",
      "failed_at": null
    }
  ],
  "count": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "summary": {
    "total_messages": 1,
    "delivered": 1,
    "sent": 0,
    "failed": 0,
    "queued": 0,
    "sending": 0,
    "delivery_rate": 100.0
  }
}
```

---

### 2. SMS History Detail & Failover Timeline
`GET /api/v1/notifications/sms/history/{id}/?company_id={uuid}`

Returns complete message details including full unmasked phone number, rendered text, voucher metadata, `can_retry` boolean, and chronological `attempts[]` array.

#### Response Example
```json
{
  "id": "4eb601cf-92a4-4676-9e1c-48af96d329ca",
  "recipient_masked": "+25575****012",
  "recipient": "0757047012",
  "phone_normalized": "+255757047012",
  "channel": "SMS",
  "message_type": "VOUCHER_SMS",
  "rendered_content": "Usimamizi Wi-Fi Voucher: R2WS-VXSS (1 Hour High Speed)",
  "status": "DELIVERED",
  "can_retry": false,
  "voucher_id": "84824d55-89f5-4422-9214-411a7e2b7e12",
  "voucher_code": "R2WS-VXSS",
  "voucher_batch_id": "183141f1-39e2-4db1-9c60-318e878593a2",
  "plan_name": "1 Hour High Speed",
  "created_at": "2026-08-30T10:10:17Z",
  "queued_at": "2026-08-30T10:10:17Z",
  "sent_at": "2026-08-30T10:10:18Z",
  "delivered_at": "2026-08-30T10:10:22Z",
  "failed_at": null,
  "attempts": [
    {
      "id": "761a5b6f-703f-4228-a3f2-1a4325712e02",
      "provider_code": "beem",
      "sender_id": "Usimamizi",
      "attempt_number": 1,
      "status": "FAILED",
      "provider_reference": "",
      "provider_status": "FAILED",
      "failure_category": "TIMEOUT",
      "failure_code": "504",
      "failure_reason": "Gateway timed out after 10s",
      "started_at": "2026-08-30T10:10:17Z",
      "completed_at": "2026-08-30T10:10:27Z"
    },
    {
      "id": "8e3b4a22-482a-4318-80f4-839572b12398",
      "provider_code": "rafikisms",
      "sender_id": "KOLOI TECH",
      "attempt_number": 2,
      "status": "SUCCESS",
      "provider_reference": "19882233",
      "provider_status": "QUEUED",
      "failure_category": "",
      "failure_code": "",
      "failure_reason": "",
      "started_at": "2026-08-30T10:10:27Z",
      "completed_at": "2026-08-30T10:10:28Z"
    }
  ]
}
```

---

### 3. Safe Retry Action
`POST /api/v1/notifications/sms/history/{id}/retry/`

#### Request Body
```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Retry Safeguards & Rules
1. **Tenant Isolation:** Enforced via company membership permission.
2. **State Gate:** Strictly allowed only for `status == 'FAILED'`. If status is `DELIVERED`, `SENT`, or `QUEUED`, returns `HTTP 400 Bad Request` with `code: "invalid_retry"`.
3. **Attempt Preservation:** Re-enters multi-provider routing engine and creates a new attempt (attempt #N+1). Previous attempt history, timestamps, and sender snapshots are permanently preserved.

---

### 4. CSV Export
`GET /api/v1/notifications/sms/history/export/?company_id={uuid}`

Generates and streams a CSV file of the filtered SMS log results (`ID, Date, Recipient, Message Type, Status, Provider, Sender ID, Attempts, Provider Reference, Voucher Code, Plan Name, Delivered At`).

---

## 3. Privacy & Masking

- In list responses and tables, recipient phone numbers are masked:
  - Canonical `+255757047012` $\rightarrow$ `+25575****012`.
- In detail modal, full normalized phone number is shown to authenticated tenant operators.

---

## 4. Summary Metrics Formula

$$\text{Delivery Rate} = \frac{\text{Delivered Messages}}{\text{Delivered Messages} + \text{Failed Messages}} \times 100\%$$

If no terminal messages exist, defaults to $100.0\%$ (if sent messages exist) or $0.0\%$ (if no messages exist).

---

## 5. Frontend Features (`/notifications/sms-history`)

- **Metric Cards:** Real-time summary counts for Total, Delivered, Failed, Queued/Sent, and Delivery Rate.
- **Quick Filters:** Tab pills for `All`, `Delivered`, `Failed`, `Pending`.
- **Search & Filters:** Search bar (phone, voucher, ref), Date From/To pickers, Provider selector, Status selector.
- **Failover Timeline Modal:** Interactive visual timeline with attempt number, provider badge, sender ID, timestamps, error diagnostics, and Retry action.
- **Responsive Layout:** Desktop table with pagination and mobile cards view ($\le 390\text{px}$) with full Dark/Light/System theme support.
