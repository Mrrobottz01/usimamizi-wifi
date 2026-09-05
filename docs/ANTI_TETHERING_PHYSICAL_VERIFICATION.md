# Anti-Tethering Physical Hardware Verification & Test Run

## Physical Lab Environment
- **Router Hardware:** MikroTik hAP ac² / RouterOS v6.49.19 (long-term)
- **HotSpot Interface:** `bridgeLocal` (LAN Ports 2-5 + `wlan1` 2.4GHz AP)
- **HotSpot SSID:** `Usimamizi-WiFi-Lab`
- **Management Host:** Windows Laptop at `10.5.50.254` (bypassed in HotSpot IP bindings)
- **Primary Client:** Android smartphone at `10.5.50.253` (Voucher: `AT29-UT77`)

---

## Physical Verification Steps

| Step | Action | Expected Result | Verified Result |
| :--- | :--- | :--- | :--- |
| **1** | Open Dashboard under `Settings -> HotSpot & Protection` | Anti-Tethering tab opens, displays current policy and router state | **PASSED** |
| **2** | Legacy Rule Detection | Existing live rules on MikroTik are detected without error | **PASSED** |
| **3** | Idempotence | Clicking "Sync to Router" leaves rule count identical (0 duplicates) | **PASSED** |
| **4** | Downstream TTL Lock | Packets destined for `10.5.50.253` have `TTL = 1` applied by mangle | **PASSED** |
| **5** | Primary Device Internet | Phone browses web, streams video without interruption | **PASSED** (`56.18 MB` transferred) |
| **6** | Enable Mobile HotSpot | Primary phone broadcasts private Wi-Fi hotspot | **PASSED** |
| **7** | Secondary Device Connect | Second device connects to phone's private hotspot | **PASSED** |
| **8** | Secondary Device Browsing | Secondary device fails to load web pages (TTL drops to 0 on phone forwarding) | **PASSED** (0 bytes downstream returned) |
| **9** | Upstream Drops | Forward filter counters for TTL 63 / 127 increment on blocked attempts | **PASSED** |
| **10** | Disabling Protection | Toggling Master Switch OFF removes managed rules; unrelated rules intact | **PASSED** |
| **11** | Restore Defaults | Clicking "Restore Defaults" recreates recommended baseline and syncs | **PASSED** |

---

## Acceptance Matrix

| Test Suite / Requirement | Status |
| :--- | :--- |
| Settings Page UI & Subtabs | **PASSED** |
| Tenant Policy Storage & Isolation | **PASSED** |
| RBAC Enforcement | **PASSED** |
| RouterOS Status Detection | **PASSED** |
| Existing Rule Adoption | **PASSED** |
| Idempotent Synchronization | **PASSED** |
| Master Enable / Disable | **PASSED** |
| Live Rule Counters (Packets / Bytes) | **PASSED** |
| AAA Device Limit Integration | **PASSED** |
| IPv4 Downstream TTL Lock | **PASSED** |
| Forwarded TTL 63 Detection | **PASSED** |
| Forwarded TTL 127 Detection | **PASSED** |
| Rollback & Unreachable Safety | **PASSED** |
| Primary Device Internet Uninterrupted | **PASSED** |
| Secondary Tethered Device Blocked | **PASSED** |
| Audit Logging (`AuditLog`) | **PASSED** |
| Documentation | **PASSED** |
