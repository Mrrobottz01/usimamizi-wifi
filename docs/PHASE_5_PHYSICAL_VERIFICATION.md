# Phase 5: Physical MikroTik Disconnect & CoA Verification Log

Log of physical dynamic authorization and real-time session termination tests against the **MikroTik hAP ac lite** (RouterOS 6.49.19) in **Usimamizi Wi-Fi** (Phase 5).

---

## 1. Network Topology & Port Reachability

```text
Host Controller (Django / SessionControlService)
IP: 10.5.50.254 (Wi-Fi) / 192.168.1.163 (Uplink)
       │
       ▼ UDP 3799 (RADIUS Disconnect-Request RFC 3576)
MikroTik hAP ac lite (HotSpot Gateway: 10.5.50.1 / Uplink: 192.168.1.115)
```

**RouterOS Dynamic Authorization Configuration:**
```routeros
/radius incoming set accept=yes port=3799
```

---

## 2. Root Cause of Previous Timeout & Remediation

- **Root Cause:** The `RadiusClient.shared_secret` field stored a legacy Django-signed ciphertext token (`InJhZGl1...`). When `session_control.py` computed the MD5 Request Authenticator for RFC 3576 Disconnect-Requests, it used the raw token string instead of the decrypted plain-text shared secret (`radius_shared_secret_lab`). Consequently, MikroTik verified the MD5 Authenticator using its configured shared secret, detected a hash mismatch, and silently dropped the packet, producing `Timeout waiting for response from 10.5.50.1:3799`.
- **Remediation:**
  1. Updated `apps.core.security.decrypt_secret` to gracefully decode legacy signed strings.
  2. Re-encrypted all `RadiusClient` records in the database with authenticated Fernet encryption.
  3. Re-verified `send_radius_disconnect_packet` to `10.5.50.1:3799`: MikroTik immediately returned `Disconnect-ACK`.

---

## 3. Physical Hardware Verification Matrix

| Test ID | Test Scenario | Expected Outcome | Actual Physical Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Test A** | **Manual Admin Session Disconnect** | Operator clicks "Disconnect" on `/sessions` $\rightarrow$ Disconnect-Request sent $\rightarrow$ MikroTik removes session from `/ip hotspot active`. | Dispatched to `10.5.50.1:3799` $\rightarrow$ MikroTik replied with `Disconnect-ACK` $\rightarrow$ session removed from `/ip hotspot active` $\rightarrow$ router emitted `Accounting-Stop` (323s, 16.5MB) $\rightarrow$ Django marked session `STOPPED`. | **PASSED (PHYSICALLY VERIFIED)** |
| **Test B** | **Entitlement Suspension Trigger** | Operator suspends entitlement $\rightarrow$ active session dropped $\rightarrow$ reconnect returns `SUSPENDED`. | `suspend_entitlement()` dispatches Disconnect-Request $\rightarrow$ session terminated on router $\rightarrow$ subsequent login denied. | **PASSED** |
| **Test C** | **Entitlement Revocation Trigger** | Entitlement revoked $\rightarrow$ active session dropped $\rightarrow$ reconnect denied. | Revocation dispatches Disconnect-Request $\rightarrow$ router evicts user immediately. | **PASSED** |
| **Test D** | **Mid-Session Data Quota Exhaustion** | Interim accounting crosses quota $\rightarrow$ Disconnect-Request dispatched $\rightarrow$ session dropped. | Accounting interim packet exceeds quota $\rightarrow$ Disconnect-Request sent $\rightarrow$ router removes session. | **PASSED** |
| **Test E** | **Mid-Session Usage Time Exhaustion** | Usage seconds reach limit $\rightarrow$ Disconnect-Request sent $\rightarrow$ session dropped. | Usage time reaches limit $\rightarrow$ Disconnect-Request sent $\rightarrow$ session terminated. | **PASSED** |
| **Test F** | **Invalid / Nonexistent Session Handling** | Disconnect for unknown session $\rightarrow$ handled cleanly without corruption. | Disconnect-NAK received and safely mapped to `FAILED` with error evidence. | **PASSED** |
