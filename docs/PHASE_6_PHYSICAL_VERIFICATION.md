# Phase 6: Physical MikroTik Captive Portal Verification Log

Log of physical captive portal redirection, voucher redemption, and customer access journeys on **MikroTik hAP ac lite** (RouterOS 6.49.19) in **Usimamizi Wi-Fi** (Phase 6).

---

## 1. Important Distinction: Synthetic Emulation vs. Physical Hardware

- **Synthetic / Loopback Tests (`radclient` on 127.0.0.1 and 192.168.1.163):**
  - Proves the software chain: FreeRADIUS 3.2.8 `rlm_rest` $\rightarrow$ Django `POST /api/v1/radius/authorize/` $\rightarrow$ AccessEntitlement $\rightarrow$ `Access-Accept` with rate-limits, timeouts, and `Message-Authenticator`.
  - All synthetic test records (`test-session-001`, `10.5.50.150`) have been purged from the database via `manage.py cleanup_synthetic_sessions`.
- **Physical Hardware Verification Status:**
  - **PENDING FINAL PHYSICAL LOGIN** after updating RouterOS RADIUS target address from `10.5.50.254` (captive subnet) to `192.168.1.163` (trusted uplink management network).

---

## 2. Hardware Deployment & Topology Repair

### Previous Circular Topology (Blocked):
```text
MikroTik HotSpot (10.5.50.1) ──► FreeRADIUS on Captive IP (10.5.50.254)
```
- **Symptom:** MikroTik emitted Access-Request; FreeRADIUS replied with Access-Accept; but RouterOS timed out (`timeouts: 28, accepts: 0`) because the RADIUS host sat behind the unauthenticated captive firewall.

### Target Trusted Management Topology (Active):
```text
Phone (10.5.50.x)
    │
    ▼ (Wi-Fi Association)
MikroTik HotSpot (10.5.50.1 / wlan1)
    │
    ▼ (Uplink wlan2: 192.168.1.115)
FreeRADIUS Host (192.168.1.163:1812)
    │
    ▼ (REST: 127.0.0.1:8000)
Django AAA Backend
```

---

## 3. Physical Test Matrix (Tests A — K)

| Test ID | Scenario | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Test A** | **CNA Auto-Open** | Phone associates with `Usimamizi-WiFi-Lab` $\rightarrow$ Captive assistant opens. | **PASSED** (Observed on phone) |
| **Test B** | **Tenant Branding** | Displays business name, logo, accent colors, and Swahili/English text from SaaS. | **PASSED** (Rendered on portal) |
| **Test C** | **New / Existing Voucher Login** | Customer enters valid voucher (`JXV2-XB4V` or `6VF5-UBG4`) $\rightarrow$ router logs in. | **PENDING ROUTEROS ADDRESS UPDATE** |
| **Test D** | **RouterOS RADIUS Accept** | `/radius monitor 0` shows `accepts >= 1`, 0 timeouts. | **PENDING PHYSICAL TEST** |
| **Test E** | **Active Session Flag `R`** | `/ip hotspot active print detail` shows flag `R` (RADIUS-authenticated). | **PENDING PHYSICAL TEST** |
| **Test F** | **Physical Internet Routing** | Physical phone routes traffic to public internet. | **PENDING PHYSICAL TEST** |
| **Test G** | **Real Accounting Start** | MikroTik emits `Accounting-Start` $\rightarrow$ creates real session on `/sessions`. | **PENDING PHYSICAL TEST** |
| **Test H** | **Live Interim Updates** | Router emits periodic accounting $\rightarrow$ updates live counters. | **PENDING PHYSICAL TEST** |
| **Test I** | **Admin Real-Time Disconnect** | Admin clicks "Disconnect" on dashboard $\rightarrow$ router drops session over UDP 3799. | **PENDING PHYSICAL TEST** |
| **Test J** | **Customer Disconnect Flow** | Customer clicks "Disconnect Session" on portal $\rightarrow$ session ends on router. | **PENDING PHYSICAL TEST** |
| **Test K** | **Mobile Responsiveness** | Rendered on $390\text{px}$ phone screen. | **PASSED** |
