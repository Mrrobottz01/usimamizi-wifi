# Hotspot Sessions Specification

Documentation of observed physical network connections and live telemetry management in **Usimamizi Wi-Fi** (Phase 4).

---

## 1. HotspotSession Model Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUIDField` (PK) | Unique session record identifier. |
| `company` | `ForeignKey(Company)` | Tenant isolation boundary. |
| `entitlement` | `ForeignKey(AccessEntitlement)` | Bound access right right. |
| `radius_client` | `ForeignKey(RadiusClient)` | Associated MikroTik router/NAS. |
| `acct_session_id` | `CharField` (Indexed) | Correlation ID assigned by RouterOS. |
| `username` | `CharField` (Indexed) | Voucher code or username. |
| `mac_address` | `CharField` (Indexed) | Canonical client device MAC (`AA:BB:CC:DD:EE:FF`). |
| `ip_address` | `GenericIPAddressField` | Assigned client IP (`10.5.50.X`). |
| `status` | `CharField` | `ACTIVE`, `STOPPED`, `STALE`. |
| `started_at` | `DateTimeField` | Session initiation timestamp. |
| `last_accounting_at` | `DateTimeField` | Most recent accounting packet timestamp. |
| `ended_at` | `DateTimeField` | Session termination timestamp. |
| `input_bytes` | `BigIntegerField` | Total client upload bytes. |
| `output_bytes` | `BigIntegerField` | Total client download bytes. |
| `session_seconds` | `PositiveIntegerField` | Elapsed connection duration. |
| `termination_reason` | `CharField` | `User-Request`, `Session-Timeout`, `Lost-Carrier`. |

---

## 2. API Endpoints

- `GET /api/v1/sessions/?company_id={uuid}&status=ACTIVE&page=1`
  - Paginated live connection list.
  - Returns `results`, `count`, `page`, `total_pages`, and `summary` (`total_sessions`, `active`, `stopped`, `stale`).
- `GET /api/v1/sessions/{id}/?company_id={uuid}`
  - Single session inspection with plan name, NAS client details, and exact byte counts.
