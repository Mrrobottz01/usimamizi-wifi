# Captive Portal Voucher Validation & Redemption Flow

Detailed state machine and redemption lifecycle for customer access in **Usimamizi Wi-Fi** (Phase 6).

---

## 1. Voucher Lifecycle in Captive Portal

```text
Customer submits voucher code "PG72-E8P8"
                 │
                 ▼
       Tenant Scoped Query
(Voucher.company == Hotspot.company)
                 │
     ┌───────────┴───────────┐
     ▼                       ▼
[AVAILABLE]             [REDEEMED]
     │                       │
     ├─► redeem_voucher()    ├─► Retrieve Entitlement
     ├─► Create Entitlement  ├─► Check is_authorizable()
     │                       │
     └───────────┬───────────┘
                 │
                 ▼
     [Authorizable == True]
                 │
                 ▼
    Return Handoff Credentials
  (username, password, router URL)
```

---

## 2. Idempotent & Concurrent Guarantees

- **AVAILABLE $\rightarrow$ REDEEMED:** Database atomic transaction with `select_for_update()` ensures 1 voucher creates exactly 1 entitlement.
- **REDEEMED Reconnects:** Customers who reconnect using an already-redeemed voucher with an active entitlement are verified and authenticated without generating duplicate entitlement rows.
- **REVOKED / EXPIRED / SUSPENDED:** Handled cleanly with localized, empathetic customer error messages.
