# Usimamizi Wi-Fi: Subscription Lifecycle Management

## 1. Architectural Distinction: Subscription vs Entitlement

A recurring concern in ISP and hotspot billing architectures is confusing the **commercial subscription** with the **network authorization grant**.

In Usimamizi:

| Dimension | `Subscription` | `AccessEntitlement` |
|---|---|---|
| **Domain** | Commercial & billing relationship | Real-time network authorization |
| **Duration** | Long-lived contract spanning multiple renewal cycles | Ephemeral grant covering exactly one validity period |
| **Consumer** | Customer identity (`+255...`) | FreeRADIUS AAA & MikroTik session check |
| **Yield** | Generates sequential entitlements across renewals | Consumed directly by NAS |

```text
┌─────────────────────────────────────────────────────────────┐
│                    Customer Identity                        │
│                     +255712345678                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Subscription (Continuous Contract)             │
│    Status: ACTIVE | Plan: 5 Mbps Monthly | Mode: MANUAL     │
│    Events: CREATED → ACTIVATED → RENEWED → RENEWED...       │
└───────────────┬──────────────────────────────┬──────────────┘
                │ Cycle 1                      │ Cycle 2 (Lossless Renewal)
                ▼                              ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│    AccessEntitlement #1      │ │     AccessEntitlement #2    │
│  Valid: Sep 1 → Oct 1        │ │   Valid: Oct 1 → Nov 1      │
│  Reference: SUB-20260901-A1  │ │   Reference: RNW-20261001-B2│
└──────────────────────────────┘ └─────────────────────────────┘
```

---

## 2. Lifecycle State Machine

```text
  ┌──────────┐
  │ PENDING  │
  └────┬─────┘
       │ Activation / Payment
       ▼
  ┌──────────┐      current_period_end reached
  │  ACTIVE  ├────────────────────────────────────┐
  └───┬──▲───┘                                    │
      │  │                                        ▼
Suspend  Reactivate                          ┌─────────┐
      │  │                                   │  GRACE  │
      ▼  │                                   └────┬────┘
  ┌───┴──┴───┐                                    │ grace_period_end reached
  │SUSPENDED │                                    ▼
  └──────────┘                               ┌─────────┐
                                             │ EXPIRED │
                                             └─────────┘
```

### State Definitions
- **`PENDING`**: Created by customer checkout or administrator draft; awaiting payment confirmation.
- **`ACTIVE`**: Fully paid and verified. FreeRADIUS authorizes RADIUS Access-Accept packets.
- **`GRACE`**: Period end passed, but within tenant grace window (e.g. 30 minutes). Customer retains connectivity while receiving urgent renewal reminders.
- **`SUSPENDED`**: Manually suspended by operator. Existing entitlements are marked `REVOKED` and RFC 3576 POD Disconnect-Requests are transmitted to MikroTik.
- **`EXPIRED`**: Period and grace window elapsed. Access severed at the router level.

---

## 3. The Lossless Renewal Rule

A customer who purchased a 24-Hour plan with 6 hours remaining who purchases another 24 hours must **never lose the 6 hours already paid for**.

### Calculation Formula:
```python
if subscription.status == SubscriptionStatus.ACTIVE and subscription.current_period_end > now:
    # Active Renewal (Lossless Extension)
    new_start = subscription.current_period_end
    new_end = subscription.current_period_end + duration
else:
    # Expired / Fresh Start
    new_start = now
    new_end = now + duration
```

The resulting `AccessEntitlement` mirrors `new_start` and `new_end`, ensuring FreeRADIUS session timeout calculations provide the true combined remaining time.

---

## 4. Background Expiry & Disconnect Workflow

Periodic Celery tasks run continuously:
1. **`process_subscription_expiries_task`**:
   - Transitions `ACTIVE` past `current_period_end` into `GRACE`.
   - Transitions `GRACE` past `grace_period_end` into `EXPIRED`.
   - Revokes underlying `AccessEntitlement` records.
   - Dispatches MikroTik Disconnect-Request (RFC 3576 POD) to disconnect live Wi-Fi sessions immediately.
2. **`send_subscription_renewal_reminders_task`**:
   - Queries subscriptions expiring in 24 hours and 1 hour.
   - Dispatches SMS renewal notifications via RafikiSMS.

---

## 5. API Reference

- `GET /api/v1/subscriptions/?company_id={id}&status={status}&q={query}`: List all subscriptions.
- `GET /api/v1/subscriptions/{id}/`: View subscription details and audit event timeline.
- `POST /api/v1/subscriptions/{id}/renew/`: Trigger manual renewal with lossless validity extension.
- `POST /api/v1/subscriptions/{id}/suspend/`: Suspend subscription and disconnect sessions.
- `POST /api/v1/subscriptions/{id}/reactivate/`: Restore unexpired subscription.
- `GET, PUT /api/v1/settings/subscriptions/`: Configure grace minutes, OTP window, and reminders.
