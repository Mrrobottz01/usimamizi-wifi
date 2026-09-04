# Phase 1 Test Results & Physical Verification Matrix

**System Name:** Usimamizi Wi-Fi  
**Phase:** Phase 1 — Local MikroTik Hotspot Lab  
**Hardware Verified:** MikroTik hAP ac lite (mipsbe, RouterOS 6.49.19 long-term)  
**Status Key:** `PASSED` | `FAILED` | `NOT TESTED` | `BLOCKED`  

---

## 1. Physical Hardware Verification Summary

> [!NOTE]
> Physical lab testing on MikroTik hAP ac lite hardware has been **100% completed and verified** by the operator. All local Hotspot authentication, captive portal UX, rate limiting, and session control policies passed.

---

## 2. Laboratory Verification Checklist

| Test Item | Verification Objective | Expected Result | Status |
| :--- | :--- | :--- | :--- |
| **1. Airtel WAN Connectivity** | Dynamic IP lease on `ether1-WAN` | `status=bound`, IP `192.168.1.109`, DNS ping to `google.com` passed (87ms avg) | **PASSED** |
| **2. Management LAN Isolation** | Admin access on `192.168.88.1` via `bridge` | WinBox/SSH connects on management IP (`ether2-5`) | **PASSED** |
| **3. Hotspot Customer Network** | DHCP lease on `10.5.50.0/24` from `wlan1` | Client receives IP `10.5.50.253`, gateway `10.5.50.1` | **PASSED** |
| **4. Captive Portal Detection** | Connecting to `Usimamizi-WiFi-Lab` triggers popup | Mobile device opens `login.usimamizi.lab` | **PASSED** |
| **5. Voucher Generator Tooling** | `generate_vouchers.py` CLI script | Clean code formatting (`R2WS-VXSS`), RouterOS import commands & Pytest (3/3 passed) | **PASSED** |
| **6. Valid Voucher Authentication** | Submit valid voucher code (`R2WS-VXSS`) | Authentication succeeds, status page renders, internet access granted | **PASSED** |
| **7. Invalid Voucher Rejection** | Submit non-existent voucher code (`INVALID-9999`) | Access rejected with error (*"invalid username or password"*) | **PASSED** |
| **8. Disabled Voucher Rejection** | Submit disabled voucher code (`68ZK-BN8A`) | Access rejected with error (*"user is disabled"*) | **PASSED** |
| **9. Simultaneous Device Policy** | Second device attempts login with active voucher | Second login rejected (`shared-users=1` limit enforced) | **PASSED** |
| **10. Bandwidth Rate Limits** | Speed test on `LAB-15MIN` profile | Upload <= 2 Mbps, Download <= 5 Mbps queue active | **PASSED** |
| **11. Session Uptime Enforcement** | Connection reaches profile limit | Session automatically disconnected by RouterOS | **PASSED** |
| **12. Operator Session Disconnect** | Remove session from `/ip hotspot active` | Client immediately disconnected, time remaining preserved on reconnect | **PASSED** |
| **13. Mobile / Desktop UX** | Captive portal pop-up & status page rendering | HTML/CSS status page displays uptime, byte counters, and logout button | **PASSED** |

---

## 3. Bandwidth Verification Table (Speed Test Results)

| Profile Name | Configured Upload | Configured Download | Observed Rate Limit | Status |
| :--- | :--- | :--- | :--- | :--- |
| **LAB-15MIN** | 2 Mbps | 5 Mbps | Enforced via RouterOS Simple Queue | **PASSED** |
| **LAB-1H** | 3 Mbps | 10 Mbps | Enforced via RouterOS Simple Queue | **PASSED** |
| **LAB-DAY** | 5 Mbps | 15 Mbps | Enforced via RouterOS Simple Queue | **PASSED** |

---

## 4. Physical Active Session Evidence

Verified active session output on physical router:

```routeros
Flags: R - radius, B - blocked 
 0    ;;; Batch: BATCH-LAB-01
      server=hotspot1 user="R2WS-VXSS" address=10.5.50.253 
      mac-address=56:E9:1A:C4:15:3E login-by="http-pap" uptime=1m11s 
      session-time-left=13m49s idle-timeout=5m keepalive-timeout=2m 
```
