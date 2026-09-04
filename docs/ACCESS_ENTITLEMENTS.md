# Access Entitlements Specification & Architecture

Comprehensive technical documentation for the **Access Entitlements** module in **Usimamizi Wi-Fi** (Phase 3 Core Domain Model).

---

## 1. Domain Concept & Role

An **`AccessEntitlement`** represents the customer's actual, verified right to use network access on a tenant's Wi-Fi network.

### Hierarchy & Relationships
```text
Plan (Commercial Product Catalog)
  │
  ▼
Voucher (Access-grant token / claim instrument)
  │
  ▼ (Atomic Voucher Redemption)
AccessEntitlement (Core Access Right + Immutable Plan Snapshot)
  │
  ▼ [Consumed in Future Phase 4]
FreeRADIUS / Network Authorization
  │
  ▼ [Consumed in Future Phase 4/5]
Active Session(s)
```

### Key Distinctions
- **Plan:** Commercial product definition (e.g. "1 Day Turbo Pass", price, bandwidth limits).
- **Voucher:** Physical or digital claim ticket containing a secure hashed redemption code.
- **AccessEntitlement:** The authoritative legal/network right to access Wi-Fi.
- **Session:** Actual connection in progress between a physical device and a router.

---

## 2. Model Schema (`AccessEntitlement`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUIDField` (PK) | Primary key. |
| `company` | `ForeignKey(Company)` | Multi-tenant isolation boundary. |
| `customer` | `ForeignKey(User, null=True)` | Customer identity link (optional in Phase 3). |
| `voucher` | `OneToOneField(Voucher, null=True)` | 1-to-1 constraint: One voucher yields maximum one entitlement. |
| `plan` | `ForeignKey(Plan)` | Source commercial product. |
| `source_type` | `CharField` | `VOUCHER`, `MANUAL`, `PAYMENT`, `PROMOTION`, `ADMIN`. |
| `status` | `CharField` | `PENDING`, `ACTIVE`, `SUSPENDED`, `EXPIRED`, `REVOKED`. |
| `reference` | `CharField` (Unique) | Concurrency-safe human reference e.g. `ENT-20260830-A8B9C1`. |
| `activated_at` | `DateTimeField` | When entitlement was activated. |
| `valid_from` | `DateTimeField` | Validity start timestamp. |
| `expires_at` | `DateTimeField` | Wall-clock expiration timestamp. |
| `validity_mode` | `CharField` | `CONTINUOUS`, `CALENDAR`, `USAGE_TIME`. |
| `download_speed_kbps` | `PositiveIntegerField` | Rate limit snapshot for download shaping. |
| `upload_speed_kbps` | `PositiveIntegerField` | Rate limit snapshot for upload shaping. |
| `data_limit_bytes` | `BigIntegerField` | Total byte quota allowance. |
| `data_used_bytes` | `BigIntegerField` | Bytes consumed by network sessions. |
| `usage_time_limit_seconds` | `PositiveIntegerField` | Total active session seconds allowance. |
| `usage_time_used_seconds` | `PositiveIntegerField` | Active connection seconds consumed. |
| `max_devices` | `PositiveIntegerField` | Maximum concurrent physical devices allowed. |
| `simultaneous_sessions` | `PositiveIntegerField` | Maximum concurrent network sessions allowed. |
| `idle_timeout_seconds` | `PositiveIntegerField` | Max inactivity before disconnection. |
| `session_timeout_seconds` | `PositiveIntegerField` | Max individual session duration. |
| `plan_snapshot` | `JSONField` | Immutable frozen dictionary of plan properties at creation. |
| `suspended_at`, `suspended_by`, `suspension_reason` | Audit Fields | Suspension audit metadata. |
| `revoked_at`, `revoked_by`, `revocation_reason` | Audit Fields | Revocation audit metadata. |

---

## 3. Plan Snapshot Strategy & Immutability

When an `AccessEntitlement` is created (via voucher redemption or manual grant), an immutable snapshot of all Plan properties is frozen into `plan_snapshot` and copied to enforcement fields:
```json
{
  "plan_id": "84824d55-89f5-4422-9214-411a7e2b7e12",
  "plan_name": "24 Hour Turbo",
  "plan_code": "ALPHA-24H",
  "duration_value": 24,
  "duration_unit": "HOURS",
  "validity_mode": "CONTINUOUS",
  "download_speed_kbps": 5120,
  "upload_speed_kbps": 2048,
  "data_limit_bytes": 1073741824,
  "max_devices": 1,
  "simultaneous_sessions": 1,
  "idle_timeout_seconds": 300,
  "session_timeout_seconds": 86400,
  "price": "3000.00",
  "currency": "TZS",
  "snapshot_created_at": "2026-08-30T10:30:00Z"
}
```

If the original `Plan` is later updated or deleted, existing entitlements remain completely unaffected.

---

## 4. API Endpoints

- `GET /api/v1/entitlements/?company_id={uuid}` — Paginated list with search, status filters, source filters, and summary metrics.
- `GET /api/v1/entitlements/{id}/?company_id={uuid}` — Detailed view with snapshot and live authorization evaluation.
- `POST /api/v1/entitlements/manual-grant/` — Grant access manually with mandatory reason.
- `POST /api/v1/entitlements/{id}/activate/` — Activate a pending entitlement.
- `POST /api/v1/entitlements/{id}/suspend/` — Suspend active access.
- `POST /api/v1/entitlements/{id}/resume/` — Resume suspended access.
- `POST /api/v1/entitlements/{id}/revoke/` — Permanently revoke access with reason.
