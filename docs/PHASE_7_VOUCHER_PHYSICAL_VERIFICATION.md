# Phase 7 — Production Voucher Management Physical Verification

**Execution Date:** 2026-09-04  
**Hardware Environment:**  
- MikroTik Router: `RB951Ui-2HnD` / `RouterOS v7.x`  
- Gateway LAN: `10.5.50.1/24` (Bridge `bridgeLocal` spanning `ether2-5` + `wlan1`)  
- HotSpot SSID: `Usimamizi-WiFi-Lab`  
- Upstream WAN: `ether1` Wired WAN (`192.168.1.107/24`) with automatic failover to `wlan2` (`G-Level 5g` / `Avie_5G`)  
- RADIUS AAA: FreeRADIUS v3 (WSL) running on ports 1812 (auth), 1813 (acct)  
- Backend: Django 5.1.15 running on `0.0.0.0:8000`  
- Frontend: Vite React SPA running on `0.0.0.0:5173` (with port 80 captive portal redirector)  
- SMS Gateway: RafikiSMS Tanzania (`KOLOI WIFI` sender ID)  

---

## 1. Automated Test Suite Results

Full automated regression test suite executed across the entire platform:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.5
django: version: 5.1.15, settings: config.settings.test
rootdir: C:\Users\fsociety\Documents\Usimamizi-wifi\backend
collected 100 items

backend\apps\accounts\tests\test_users.py ..                             [  2%]
backend\apps\companies\tests\test_public_portal.py .......               [  9%]
backend\apps\companies\tests\test_tenant_isolation.py .                  [ 10%]
backend\apps\core\tests\test_health.py .                                 [ 11%]
backend\apps\entitlements\tests\test_entitlements.py ........            [ 19%]
backend\apps\hotspot_sessions\tests\test_session_control.py ..........   [ 29%]
backend\apps\hotspot_sessions\tests\test_sessions.py ..                  [ 31%]
backend\apps\notifications\tests\test_notifications.py .                 [ 32%]
backend\apps\notifications\tests\test_rafikisms_adapter.py ...           [ 35%]
backend\apps\notifications\tests\test_sender_ids.py ....                 [ 39%]
backend\apps\notifications\tests\test_sms.py ..                          [ 41%]
backend\apps\notifications\tests\test_sms_history.py .......             [ 48%]
backend\apps\payments\tests\test_payments_api.py .....                   [ 53%]
backend\apps\payments\tests\test_purchase_flow.py ......                 [ 59%]
backend\apps\payments\tests\test_walled_garden.py ..                     [ 61%]
backend\apps\payments\tests\test_webhook.py ...                          [ 64%]
backend\apps\plans\tests\test_plans.py ..                                [ 66%]
backend\apps\radius\tests\test_radius.py ..........                      [ 76%]
backend\apps\vouchers\tests\test_vouchers.py ..........                  [ 86%]
backend\apps\notifications\tests\test_rafikisms_adapter.py .......       [ 93%]
backend\apps\notifications\tests\test_sender_ids.py .                    [ 94%]
backend\apps\notifications\tests\test_sms.py .                           [ 95%]
backend\apps\payments\tests\test_snippe_adapter.py .....                 [100%]

============================ 100 passed in 11.69s =============================
```

**Result:** 100 passed, 0 failed.

---

## 2. Physical Verification Steps & Live Test Evidence

### Test 1: Batch Generation & Code Normalization
- **Batch Generated:** `VB-20260904-8BQDQC` (5 vouchers for plan `3 Minutes Test Pass`)
- **Generated Codes:**
  - `GQGR-EWV4`
  - `BSYY-UTRK`
  - `KAVH-G6CE`
  - `5D78-654J`
  - `CQ9W-EFGR`
- **Normalization Test:**
  - Input: `gqgr ewv4` (lowercase, space separated)
  - Normalized: `GQGR-EWV4`
  - Database lookup: Match found via `display_code` and `code_hash`.

### Test 2: Public Captive Portal Redemption
- **Endpoint:** `POST /api/v1/public/hotspots/usimamizi-lab/voucher/`
- **Request:**
  ```json
  {
    "voucher_code": "gqgr ewv4",
    "language": "EN"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "username": "GQGR-EWV4",
    "password": "GQGR-EWV4",
    "entitlement_reference": "ENT-20260904-2CB71A",
    "plan_name": "3 Minutes Test Pass",
    "download_speed_kbps": 5000,
    "upload_speed_kbps": 2000,
    "remaining_seconds": 179,
    "remaining_data_bytes": null,
    "router_login_url": "http://10.5.50.1/login"
  }
  ```

### Test 3: FreeRADIUS Authorization & Dynamic Attribute Enforcement
- **Client:** `radclient -x 127.0.0.1:1812 auth testing123`
- **Request:**
  ```text
  User-Name = "GQGR-EWV4"
  User-Password = "GQGR-EWV4"
  NAS-IP-Address = 10.5.50.1
  ```
- **Live FreeRADIUS Response:**
  ```text
  Received Access-Accept Id 51 from 127.0.0.1:1812 to 127.0.0.1:41443 length 99
  	Session-Timeout = 152
  	Idle-Timeout = 300
  	Acct-Interim-Interval = 60
  	Mikrotik-Rate-Limit = "2000k/5000k"
  	WISPr-Bandwidth-Max-Down = 5000000
  	WISPr-Bandwidth-Max-Up = 2000000
  ```

### Test 4: Voucher Reservation Lifecycle
- **Voucher:** `KAVH-G6CE`
- **Customer Phone:** `0788112233`
- **Distribution State:** `SOLD`
- **Action:** Transitioned from `AVAILABLE` to `RESERVED`.
- **Portal Login:** Customer redeemed `kavh-g6ce` successfully.
- **Entitlement Created:** `ENT-20260904-4C10CA` (Active, 179 seconds remaining).
- **FreeRADIUS Auth:** Returned `Access-Accept` with `Session-Timeout = 165` and `Mikrotik-Rate-Limit = "2000k/5000k"`.

### Test 5: Cascading Revocation & RFC 3576 POD Disconnect
- **Action:** Admin revoked redeemed voucher `GQGR-EWV4` with reason `"Physical verification test revocation"`.
- **Voucher Status:** Changed from `REDEEMED` to `REVOKED`.
- **Entitlement Status:** Changed from `ACTIVE` to `REVOKED`.
- **FreeRADIUS Auth Re-Check:**
  ```text
  Received Access-Reject Id 231 from 127.0.0.1:1812 to 127.0.0.1:42242 length 63
  	Reply-Message = "Access denied: REVOKED."
  ```
- **MikroTik Port 3799 Status:** `/radius/incoming/print` confirms incoming POD accept is `true` on port `3799`.

### Test 6: A4 Multi-Card Printable Voucher Sheet
- **Endpoint:** `GET /api/v1/voucher-batches/2bb11122-7427-4a6a-80a1-affc7e81c4f5/printable-cards/`
- **Generated Cards:** 5 cards with Hotspot SSID `Usimamizi-WiFi-Lab`, Plan Name, Price (`500.00 TZS`), Bold monospace code, and live QR URL: `http://login.usimamizi.lab:5173/p/usimamizi-lab?voucher=5D78-654J`.

### Test 7: RouterOS Fallback Script Export (`.rsc`)
- **Export Command:** `export_batch_routeros_script(batch)`
- **Header:** `# SOURCE: USIMAMIZI_LOCAL_FALLBACK | BATCH: VB-20260904-8BQDQC`
- **Export Badge:** Batch updated to `EXPORTED_ROUTEROS`.
