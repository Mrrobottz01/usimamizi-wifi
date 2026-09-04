# Frozen Radius Code Review Notes — Phase 3 Review

This document records the frozen code review of `backend/apps/radius/` and `infrastructure/freeradius/` following the completion of **Phase 3 (Access Entitlements & Access Lifecycle)**.

---

## 1. Scope Audit

Per Phase 3 scope rules, `backend/apps/radius/` and `infrastructure/freeradius/` remained **strictly frozen and unmodified**. All 3 existing RADIUS tests passed with zero regressions.

---

## 2. Architectural Hand-off for Phase 4 (FreeRADIUS & Central AAA Redesign)

With `AccessEntitlement` now complete, Phase 4 should refactor the RADIUS authorization path as follows:

1. **Authorization Target:**
   - FreeRADIUS `AuthorizeView` in `apps/radius/` must consume `AccessEntitlement` via `is_entitlement_authorizable()` rather than querying `Voucher` directly.
2. **Reply Attributes from Immutable Plan Snapshot:**
   - `WISPr-Bandwidth-Max-Down` $\leftarrow$ `entitlement.download_speed_kbps * 1000`
   - `WISPr-Bandwidth-Max-Up` $\leftarrow$ `entitlement.upload_speed_kbps * 1000`
   - `Session-Timeout` $\leftarrow$ `entitlement.session_timeout_seconds` or remaining continuous/usage validity seconds.
   - `Idle-Timeout` $\leftarrow$ `entitlement.idle_timeout_seconds`.
3. **Session Accounting Updates:**
   - Accounting Interim-Update and Stop packets in Phase 4/5 will atomically increment `data_used_bytes` (`Acct-Input-Octets` + `Acct-Output-Octets`) and `usage_time_used_seconds` (`Acct-Session-Time`).
