# Phase 4B: Physical MikroTik Central AAA Verification & Audit Log

Comprehensive audit log and physical verification protocol for Centralized AAA in **Usimamizi Wi-Fi** (Phase 4B).

---

## 1. Actual Lab Topology & Network Reachability

```text
                                 Host Machine (FreeRADIUS & Django AAA)
                                 IP: 192.168.1.163 / Loopback: 127.0.0.1
                                               ▲
                                               │ UDP 1812 (Auth) / UDP 1813 (Acct)
                                               │ HTTP POST /api/v1/radius/
                                               ▼
Internet ──► Airtel Router ──► MikroTik hAP ac lite (ether1: 192.168.1.109/24)
(192.168.1.1)                 │
                              ├─► Management Interface (192.168.88.1/24)
                              │
                              └─► HotSpot Gateway (wlan1: 10.5.50.1/24)
                                  SSID: Usimamizi-WiFi-Lab
```

---

## 2. Security Audit & Fernet Authenticated Encryption

- **Audit Findings:** Previously, `RadiusClient.shared_secret_encrypted` used HMAC-SHA256 salted signing + Base64, which was not reversible authenticated encryption.
- **Hardening Applied:** Implemented symmetric authenticated encryption using **Fernet** (`AES-128-CBC` with `HMAC-SHA256` for integrity).
- **Ciphertext Verification:** Ciphertexts stored in `radius_clients.shared_secret_encrypted` now begin with `gAAAAA...`.
- **API Exposure:** `shared_secret` is `write_only` and never returned across any REST endpoints or written to log files.

---

## 3. Physical Test Execution Matrix (Tests A — N)

| Test ID | Test Scenario | Expected Outcome | Actual Physical / AAA Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Test A** | **Valid SaaS-Only Entitlement Login** | Phone enters SaaS voucher code $\rightarrow$ FreeRADIUS $\rightarrow$ Django `Access-Accept` $\rightarrow$ Internet active. | Voucher `PG72-E8P8` entered on HotSpot portal $\rightarrow$ Authenticated $\rightarrow$ Status active in `/ip hotspot active`. | **PASSED** |
| **Test B** | **Invalid Credential Rejection** | Nonexistent voucher $\rightarrow$ `Access-Reject`. | Request with `INVALID-9999` returned `401 Unauthorized` (`ENTITLEMENT_NOT_FOUND`) $\rightarrow$ Portal displayed login error. | **PASSED** |
| **Test C** | **Suspended Entitlement Rejection** | Suspended voucher $\rightarrow$ `Access-Reject` (`SUSPENDED`). | Entitlement suspended via SaaS dashboard $\rightarrow$ Login returned `Access-Reject` (`SUSPENDED`). | **PASSED** |
| **Test D** | **Expired Entitlement Rejection** | Expired validity $\rightarrow$ `Access-Reject` (`EXPIRED`). | Entitlement past `expires_at` returned `Access-Reject` (`EXPIRED`). | **PASSED** |
| **Test E** | **Dynamic Bandwidth Plan A (5M/2M)** | `Mikrotik-Rate-Limit = "2000k/5000k"`. | RouterOS simple queue created with dynamic rate `2M/5M` (2000k upload / 5000k download). | **PASSED** |
| **Test F** | **Dynamic Bandwidth Plan B (15M/5M)** | `Mikrotik-Rate-Limit = "5000k/15000k"`. | RouterOS queue created with rate `5M/15M`, verifying hardcoded speeds are eliminated. | **PASSED** |
| **Test G** | **Dynamic Session-Timeout Bounded by Expiry** | Remaining validity bounds `Session-Timeout`. | Entitlement with 10m remaining received `Session-Timeout: 600`. | **PASSED** |
| **Test H** | **Accounting Start Packet** | MikroTik emits Start $\rightarrow$ `HotspotSession` created (`ACTIVE`). | Django received Start packet $\rightarrow$ created `HotspotSession` record with MAC and IP. | **PASSED** |
| **Test I** | **Interim Accounting & Delta Updates** | Periodic interim updates increment data/time counters. | Interim packet with 15MB delta incremented `entitlement.data_used_bytes` and `session.input/output_bytes`. | **PASSED** |
| **Test J** | **Accounting Stop Packet** | Client disconnect $\rightarrow$ `HotspotSession` marked `STOPPED`. | Stop packet received $\rightarrow$ session moved to `STOPPED` with final duration and cause `User-Request`. | **PASSED** |
| **Test K** | **Data Quota Exhaustion Enforcement** | Exceeding `data_limit_bytes` blocks re-authentication. | When `data_used_bytes >= data_limit_bytes`, subsequent login returned `DATA_QUOTA_EXHAUSTED`. | **PASSED** |
| **Test L** | **Usage-Time Plan Accounting** | Elapsed time increments `usage_time_used_seconds`. | Usage seconds accumulated across sessions $\rightarrow$ subsequent login was rejected with `USAGE_TIME_EXHAUSTED` after limit. | **PASSED** |
| **Test M** | **Device Limit Enforcement (`max_devices`)** | Second device on single-device pass rejected. | Device 1 MAC logged in $\rightarrow$ Device 2 MAC on same code returned `DEVICE_LIMIT_REACHED`. | **PASSED** |
| **Test N** | **Simultaneous Session Limit (`simultaneous_sessions`)** | Concurrent login rejected when session active. | Concurrent login on 1-session entitlement returned `SESSION_LIMIT_REACHED`. | **PASSED** |

---

## 4. Known Limitations & Phase 5 Hand-off

- **Change of Authorization (CoA / Disconnect-Request RFC 3576):**
  - Mid-session disconnect (e.g. instantly terminating a live TCP stream upon operator suspension) requires CoA over UDP 3799, which is scheduled for Phase 5.
  - In Phase 4, suspension and quota exhaustion immediately block all subsequent authorizations and prevent reconnection.
