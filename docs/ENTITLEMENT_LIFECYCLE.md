# Entitlement Lifecycle State Machine & Authorization Evaluation

Documentation of state transitions, transition invariants, and authorization decision rules for **Usimamizi Wi-Fi** (Phase 3).

---

## 1. Lifecycle State Machine

```text
       ┌──────────────┐
       │   PENDING    │
       └──────┬───────┘
              │ activate_entitlement()
              ▼
       ┌──────────────┐
       │    ACTIVE    │◄──────────────┐
       └──┬───┬───────┘               │
          │   │                       │ resume_entitlement()
          │   │ suspend_entitlement() │
          │   ▼                       │
          │ ┌──────────────┐          │
          │ │  SUSPENDED   ├──────────┘
          │ └──┬───────────┘
          │    │
          │    │ revoke_entitlement()
          │    ▼
          │ ┌──────────────┐
          ├─┤   REVOKED    │ (Terminal)
          │ └──────────────┘
          │
          │ expire_entitlement() / celery task
          ▼
       ┌──────────────┐
       │   EXPIRED    │ (Terminal)
       └──────────────┘
```

---

## 2. Allowed Transitions Matrix

| Current State | Target State | Service Method | Permitted? |
| :--- | :--- | :--- | :--- |
| `PENDING` | `ACTIVE` | `activate_entitlement()` | **YES** |
| `PENDING` | `REVOKED` | `revoke_entitlement()` | **YES** |
| `ACTIVE` | `SUSPENDED` | `suspend_entitlement()` | **YES** |
| `ACTIVE` | `REVOKED` | `revoke_entitlement()` | **YES** |
| `ACTIVE` | `EXPIRED` | `expire_entitlement()` | **YES** |
| `SUSPENDED` | `ACTIVE` | `resume_entitlement()` | **YES** |
| `SUSPENDED` | `REVOKED` | `revoke_entitlement()` | **YES** |
| `EXPIRED` | *Any* | - | **NO** (Terminal) |
| `REVOKED` | *Any* | - | **NO** (Terminal) |

---

## 3. Authorization Decision Evaluator (`is_entitlement_authorizable`)

This evaluator will be called by FreeRADIUS in Phase 4 during Access-Request evaluation:

```text
Access-Request (RADIUS)
          │
          ▼
is_entitlement_authorizable(entitlement)
          │
          ├─► Status == REVOKED ─────────────► (False, "REVOKED")
          ├─► Status == SUSPENDED ───────────► (False, "SUSPENDED")
          ├─► Status == EXPIRED ─────────────► (False, "EXPIRED")
          ├─► Status != ACTIVE ──────────────► (False, "NOT_ACTIVE")
          ├─► valid_from > now ──────────────► (False, "NOT_YET_VALID")
          ├─► expires_at <= now ─────────────► (False, "EXPIRED")
          ├─► data_used >= data_limit ───────► (False, "DATA_QUOTA_EXHAUSTED")
          ├─► time_used >= time_limit ───────► (False, "USAGE_TIME_EXHAUSTED")
          │
          └─► All Checks Pass ───────────────► (True, "AUTHORIZED")
```
