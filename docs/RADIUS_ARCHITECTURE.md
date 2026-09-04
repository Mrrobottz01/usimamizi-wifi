# RADIUS & Central AAA Architecture (Phase 4)

Comprehensive architectural documentation of the Centralized AAA system in **Usimamizi Wi-Fi** connecting physical MikroTik HotSpots, FreeRADIUS, and Django SaaS.

---

## 1. Architectural Role & Principles

In Phase 4, Centralized AAA is completely redesigned so that **`AccessEntitlement`** (and its immutable plan snapshot) is the single authoritative source of truth for all access decisions.

```text
MikroTik HotSpot
      │  (RADIUS Access-Request / Accounting)
      ▼
FreeRADIUS (rlm_rest)
      │  (HTTP REST Authorization & Accounting)
      ▼
Django AAA API (/api/v1/radius/)
      │
      ├─► Validate Authorized NAS (RadiusClient) & Tenant Context
      │
      ├─► Resolve AccessEntitlement (Voucher / Reference / Customer)
      │
      ├─► is_entitlement_authorizable()
      │     ├── Status (ACTIVE)
      │     ├── Validity Bounds (valid_from <= now < expires_at)
      │     ├── Data Quota (data_used < data_limit)
      │     ├── Usage Time Quota (time_used < time_limit)
      │     ├── Device Limit (max_devices)
      │     └── Simultaneous Sessions Limit (simultaneous_sessions)
      │
      ├─► Generate Dynamic Reply Attributes
      │     ├── Mikrotik-Rate-Limit: rx-rate/tx-rate (Upload/Download)
      │     ├── WISPr-Bandwidth-Max-Down / Up
      │     ├── Session-Timeout (bounded dynamically)
      │     ├── Idle-Timeout
      │     └── Acct-Interim-Interval
      │
      ▼
Access-Accept / Access-Reject
```

---

## 2. Key Domain Boundaries

1. **`RadiusClient`:** Represents an authorized MikroTik NAS router within a tenant (`Company`). Validates `nas_ip`, `nas_identifier`, and encrypts shared secrets at rest.
2. **`AccessEntitlement`:** Legal/network access right purchased by customer with immutable plan snapshot.
3. **`HotspotSession`:** Physical observed connection between a device and router (`started_at`, `input_bytes`, `output_bytes`, `session_seconds`, `status`).
4. **`RadiusAccountingLog`:** Raw immutable packet audit stream for protocol evidence.
5. **`EntitlementDevice`:** Normalized device MAC address bound to entitlement for `max_devices` enforcement.
