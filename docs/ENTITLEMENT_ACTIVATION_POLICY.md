# Entitlement Activation Policy & Rules

Documentation of activation behaviors and lifecycle triggers for Access Entitlements in **Usimamizi Wi-Fi** (Phase 3).

---

## 1. Chosen Default Policy for Phase 3

### Voucher Redemption $\rightarrow$ Immediate Activation
In current Phase 2 & 3 captive portal operations, when a customer redeems a voucher (or an operator issues a manual grant):
1. An `AccessEntitlement` is created.
2. `status` is set immediately to **`ACTIVE`**.
3. `activated_at` is stamped to `timezone.now()`.
4. `valid_from` and `expires_at` are calculated.

```text
Voucher AVAILABLE
       │
       ▼ (redeem_voucher)
[Atomic DB Transaction]
├── Voucher -> REDEEMED
└── AccessEntitlement -> ACTIVE (activated_at = now)
```

---

## 2. Future Delayed Activation Architecture

The engine natively supports delayed activation for advanced business workflows (e.g. hotel pre-issuance or retail advance purchase):
- `activate_immediately = False` creates the entitlement in `status = PENDING`.
- The first network login or customer activation API call triggers `activate_entitlement(entitlement=...)`, starting the validity clock.

---

## 3. Activation Guardrails & Invariants

1. **Re-activation Rejection:** An entitlement that is already `ACTIVE`, `SUSPENDED`, `EXPIRED`, or `REVOKED` cannot be activated again via `activate_entitlement()`.
2. **Revocation Immutability:** Revoked entitlements can never be restored to `ACTIVE`.
3. **One Voucher Constraint:** A voucher can only be redeemed once. Attempts to redeem an already-redeemed voucher fail and produce 0 duplicate entitlements.
