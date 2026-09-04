# Phase 4 Walkthrough — FreeRADIUS & Central AAA Redesign

Architectural walkthrough and verification overview of **Phase 4: FreeRADIUS & Central AAA Redesign**.

---

## 1. Executive Summary

Phase 4 redesigns FreeRADIUS and the Centralized AAA engine so that all network authorization decisions are evaluated strictly against **`AccessEntitlement`** and its frozen plan snapshot. Hard-coded rate limits and package values have been completely eliminated.

---

## 2. Redesigned Components

1. **`RadiusClient` (NAS / Router Security):**
   - Tenant-scoped router entity with encrypted shared secrets at rest.
   - Fail-closed validation for unauthorized or disabled routers.

2. **`authorize_radius_access()`:**
   - Evaluates `is_entitlement_authorizable()`.
   - Enforces `max_devices` via `EntitlementDevice` bindings.
   - Enforces `simultaneous_sessions` by querying active `HotspotSession` records.
   - Generates dynamic rate limiting (`Mikrotik-Rate-Limit = "{upload_k}k/{download_k}k"`), `WISPr-Bandwidth-Max-Down/Up`, `Session-Timeout`, and `Idle-Timeout`.

3. **`process_radius_accounting()`:**
   - Computes 64-bit gigaword octet sums ($2^{32} \times \text{gigawords} + \text{octets}$).
   - Calculates positive cumulative deltas to prevent double-counting.
   - Updates `HotspotSession` and increments `entitlement.data_used_bytes` / `usage_time_used_seconds` atomically.
   - Provides out-of-order and duplicate packet protections.

4. **Frontend `ActiveSessionsPage.tsx`:**
   - Real-time connection monitoring dashboard at `/sessions`.
   - Shows user/code, MAC, IP, plan, NAS, status, duration, and download/upload data transfers.

---

## 3. Verification Summary

```text
Backend Pytest Suite: 57 passed in 7.13s
Ruff Linter: 0 errors
TypeScript Compiler: 0 errors
ESLint: 0 errors, 0 warnings
Vite Production Build: Clean build in 4.93s
Vitest Suite: 1 passed
```
