# Phase 3 Walkthrough — Access Entitlements & Access Lifecycle

Comprehensive architectural summary and verification walkthrough for **Phase 3 — Access Entitlements & Access Lifecycle**.

---

## 1. Domain Overview

Phase 3 establishes the primary domain entity that represents:
> **The customer's actual, verified right to use network access on a tenant's Wi-Fi network: `AccessEntitlement`.**

```text
Plan (Catalog) ────> Voucher (Token) ────> AccessEntitlement (Access Right) ────> Future RADIUS Auth
```

---

## 2. Key Components Built

### Backend (`backend/apps/entitlements/`)
1. **Model (`AccessEntitlement`):**
   - Implements multi-tenancy (`company`), voucher link (`OneToOneField` with `vouchers.Voucher`), plan reference, source types (`VOUCHER`, `MANUAL`), and lifecycle statuses (`PENDING`, `ACTIVE`, `SUSPENDED`, `EXPIRED`, `REVOKED`).
   - Immutable snapshot storage in `plan_snapshot` JSON field.
   - Enforcement fields: `download_speed_kbps`, `upload_speed_kbps`, `data_limit_bytes`, `data_used_bytes`, `usage_time_limit_seconds`, `usage_time_used_seconds`, `max_devices`, `simultaneous_sessions`.
2. **Services & Selectors:**
   - `create_entitlement_from_plan()`: Freezes Plan properties into snapshot and assigns unique reference (`ENT-YYYYMMDD-XXXXXX`).
   - `calculate_entitlement_validity()`: Timezone-aware date calculations for `CONTINUOUS`, `CALENDAR` (with month boundary arithmetic), and `USAGE_TIME`.
   - `activate_entitlement()`, `suspend_entitlement()`, `resume_entitlement()`, `revoke_entitlement()`, `expire_entitlement()`.
   - `grant_manual_entitlement()`: Creates manual access entitlement with mandatory operator reason and audit log.
   - `is_entitlement_authorizable()`: Prepares authorization decision foundation for Phase 4 FreeRADIUS.
   - `get_entitlements_queryset()` & `calculate_entitlement_summary_metrics()`.
3. **Tasks:**
   - `expire_due_entitlements()`: Idempotent periodic task processing expired active entitlements in bounded batches.
4. **Voucher Integration:**
   - Upgraded `redeem_voucher()` to create `AccessEntitlement` atomically.

### Frontend SPA (`frontend/src/features/entitlements/`)
1. **`EntitlementsListPage.tsx`:**
   - Summary cards: Active, Expiring Soon, Suspended, Expired.
   - Quick filters (`All`, `Active`, `Expiring Soon`, `Suspended`, `Expired`, `Revoked`), source filter, search bar.
   - Responsive desktop table and mobile cards view ($\le 390\text{px}$).
2. **`EntitlementDetailView.tsx`:**
   - Detailed modal showing Plan snapshot, authorization status, bandwidth rate limits, quota consumption, and audit timeline.
3. **`ManualGrantModal.tsx`, `SuspendModal.tsx`, `RevokeModal.tsx`:**
   - Action dialogs with validation and reason inputs.

---

## 3. Automated Verification

- **Backend Pytest:** 48 passed in 1.92s
- **Ruff Linter:** 0 errors
- **TypeScript:** 0 errors
- **ESLint:** 0 errors, 0 warnings
- **Vite Production Build:** Clean build in 8.34s
- **Vitest Suite:** 1 passed
