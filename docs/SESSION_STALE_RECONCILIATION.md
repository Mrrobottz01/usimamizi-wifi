# Session Stale Reconciliation & Policy Specification

Specification for identifying, transitioning, and handling inactive/abandoned HotSpot sessions in **Usimamizi Wi-Fi** (Phase 5).

---

## 1. Semantics of Session Statuses

- **`ACTIVE`:** Physical network connection with active traffic / recent accounting updates.
- **`STOPPED`:** Authoritatively terminated by RouterOS via `Accounting-Request (Acct-Status-Type = Stop)`.
- **`STALE`:** No accounting packet received within `RADIUS_SESSION_STALE_AFTER_SECONDS` (default: 300 seconds).

---

## 2. Simultaneous Session Calculation Policy

To prevent orphaned or ungracefully disconnected devices (e.g. phone ran out of battery or walked away out of Wi-Fi range without sending Stop) from permanently exhausting `simultaneous_sessions`:

- `get_active_sessions_count_for_entitlement()` filters for sessions with `status = ACTIVE` where `last_accounting_at >= (now - STALE_THRESHOLD)`.
- Stale sessions are automatically excluded from the count, allowing legitimate reconnection while preserving audit logs.
