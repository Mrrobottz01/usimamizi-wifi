# RADIUS Authorization Flow & Dynamic Attribute Calculation

Documentation of authorization evaluation, denial reasons, and dynamic attribute synthesis for **Usimamizi Wi-Fi** (Phase 4).

---

## 1. Authorization Step-by-Step

When FreeRADIUS calls `POST /api/v1/radius/authorize/`:

1. **NAS Resolution & Tenant Isolation:**
   - Lookup `RadiusClient` by `nas_ip` or `nas_identifier`.
   - If not found $\rightarrow$ Reject with `UNKNOWN_NAS`.
   - If `is_active == False` $\rightarrow$ Reject with `NAS_DISABLED`.
   - Resolve tenant company `company = nas.company`. All subsequent queries are strictly scoped to `company`.

2. **Entitlement Resolution:**
   - Find `Voucher` matching `display_code` $\rightarrow$ `voucher.entitlement`.
   - Or find `AccessEntitlement` matching `reference`.
   - Or lookup registered `User` account.
   - If not found $\rightarrow$ Reject with `ENTITLEMENT_NOT_FOUND`.

3. **Lifecycle & Quota Evaluation (`is_entitlement_authorizable`):**
   - If `status == SUSPENDED` $\rightarrow$ Reject with `SUSPENDED`.
   - If `status == REVOKED` $\rightarrow$ Reject with `REVOKED`.
   - If `status == EXPIRED` or `now >= expires_at` $\rightarrow$ Reject with `EXPIRED`.
   - If `data_used_bytes >= data_limit_bytes` $\rightarrow$ Reject with `DATA_QUOTA_EXHAUSTED`.
   - If `usage_time_used_seconds >= usage_time_limit_seconds` $\rightarrow$ Reject with `USAGE_TIME_EXHAUSTED`.
   - If `status != ACTIVE` $\rightarrow$ Reject with `NOT_ACTIVE`.

4. **Device Limit Policy (`max_devices`):**
   - Normalize MAC address (`AA:BB:CC:DD:EE:FF`).
   - If device is not already bound to this entitlement and current device count $\ge$ `max_devices` $\rightarrow$ Reject with `DEVICE_LIMIT_REACHED`.
   - Otherwise, bind device in `EntitlementDevice`.

5. **Simultaneous Session Policy (`simultaneous_sessions`):**
   - Count active `HotspotSession` records for entitlement.
   - If `active_sessions >= simultaneous_sessions` $\rightarrow$ Reject with `SESSION_LIMIT_REACHED`.

6. **Dynamic Session-Timeout Calculation:**
   $$\text{session\_timeout} = \min(\text{plan\_timeout}, \text{continuous\_validity\_seconds\_remaining}, \text{usage\_quota\_seconds\_remaining})$$
   - If computed `session_timeout <= 0` $\rightarrow$ Reject with `EXPIRED`.

7. **Construct Reply Attributes:**
   - `Mikrotik-Rate-Limit`: `"{upload_kbps}k/{download_kbps}k"`
   - `WISPr-Bandwidth-Max-Down`: `download_kbps * 1000`
   - `WISPr-Bandwidth-Max-Up`: `upload_kbps * 1000`
   - `Session-Timeout`: `session_timeout`
   - `Idle-Timeout`: `entitlement.idle_timeout_seconds or 300`
   - `Acct-Interim-Interval`: `60`

---

## 2. Normalized Denial Reasons

| Internal Reason Code | User Message | HTTP Status |
| :--- | :--- | :--- |
| `UNKNOWN_NAS` | NAS router is unauthorized or unknown. | 401 |
| `NAS_DISABLED` | NAS router is disabled. | 401 |
| `ENTITLEMENT_NOT_FOUND` | No active access entitlement found. | 401 |
| `INVALID_CREDENTIAL` | Invalid password. | 401 |
| `SUSPENDED` | Access denied: SUSPENDED. | 401 |
| `REVOKED` | Access denied: REVOKED. | 401 |
| `EXPIRED` | Access denied: EXPIRED. | 401 |
| `DATA_QUOTA_EXHAUSTED` | Access denied: DATA_QUOTA_EXHAUSTED. | 401 |
| `USAGE_TIME_EXHAUSTED` | Access denied: USAGE_TIME_EXHAUSTED. | 401 |
| `DEVICE_LIMIT_REACHED` | Maximum allowed devices reached for this access pass. | 401 |
| `SESSION_LIMIT_REACHED` | Simultaneous session limit reached. | 401 |
