# Session Disconnect Workflow & Lifecycle Architecture

Detailed lifecycle and architectural state transitions for real-time session termination in **Usimamizi Wi-Fi** (Phase 5).

---

## 1. Disconnect Triggers

| Trigger Type | Source | Description |
| :--- | :--- | :--- |
| `MANUAL` | Admin / Operator UI | Staff clicks "Disconnect" on `/sessions` dashboard. |
| `ENTITLEMENT_SUSPENDED` | Entitlement Lifecycle | Operator suspends an `AccessEntitlement`. |
| `ENTITLEMENT_REVOKED` | Entitlement Lifecycle | Operator revokes an `AccessEntitlement`. |
| `DATA_QUOTA_EXHAUSTED` | Accounting Processor | Accounting update crosses `data_limit_bytes`. |
| `USAGE_TIME_EXHAUSTED` | Accounting Processor | Accounting update crosses `usage_time_limit_seconds`. |
| `ADMIN_SECURITY_ACTION` | Security Automation | Fraud or suspicious device activity detected. |

---

## 2. Decoupled Business Lifecycle & Network Resilience

```text
Database Action (suspend_entitlement / revoke_entitlement)
        │
        ├─► Entitlement Status Committed (SUSPENDED / REVOKED)
        │
        ├─► Disconnect Requests Enqueued
        │
        ▼
Network Dispatch (UDP 3799 to MikroTik)
        │
        ├─► Success: Disconnect-ACK received -> SessionDisconnectRequest.status = ACKNOWLEDGED
        │
        └─► Failure/Timeout: SessionDisconnectRequest.status = TIMEOUT / FAILED
             (Database state remains SUSPENDED; reconnect attempts will be rejected)
```

---

## 3. DisconnectRequest Status Lifecycle

```text
[PENDING] ──► [SENDING] ──┬─► [ACKNOWLEDGED] (Router accepted Disconnect-Request)
                          ├─► [FAILED]       (Disconnect-NAK or invalid NAS)
                          └─► [TIMEOUT]      (No response within max attempts)
```
