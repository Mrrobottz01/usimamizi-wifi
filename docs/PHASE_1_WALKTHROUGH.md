# Phase 1 Walkthrough & Physical Verification Summary

**Phase:** Phase 1 — Local MikroTik Hotspot & Voucher Lab  
**Hardware Verified:** MikroTik hAP ac lite (mipsbe, RouterOS 6.49.19 long-term)  
**Status:** **PHASE 1 100% COMPLETE & PHYSICALLY VERIFIED**  

---

## 1. Summary of Verified Physical Achievements

1. **Upstream WAN Integration:** `ether1-WAN` bound dynamically to Airtel router (`192.168.1.109/24`), gateway `192.168.1.1`, DNS resolution verified (ping `google.com` 87ms avg).
2. **Management & Customer Isolation:** Management network preserved on `ether2-5` (`bridge`, `192.168.88.1/24`). Wireless interface `wlan1` isolated with dedicated subnet `10.5.50.0/24`, pool `10.5.50.10-254`, and DHCP server `dhcp-hotspot`.
3. **Wi-Fi Hotspot Service:** SSID `Usimamizi-WiFi-Lab` running on `wlan1` with HotSpot server `hotspot1` (`login.usimamizi.lab`).
4. **Local Voucher Profiles:** Configured and verified test profiles:
   - `LAB-15MIN` (15m timeout, 2M/5M rate limit, 1 device)
   - `LAB-1H` (1h timeout, 3M/10M rate limit, 1 device)
   - `LAB-DAY` (24h timeout, 5M/15M rate limit, 1 device)
5. **Captive Portal Deployment:** Deployed custom lightweight HTML/CSS captive portal templates (`login.html`, `status.html`, `logout.html`, `errors.html`, `style.css`) to `/flash/hotspot`.
6. **Physical Authentication & Policy Verification:**
   - Active device (`56:E9:1A:C4:15:3E`) assigned IP `10.5.50.253`, authenticated via voucher `R2WS-VXSS`.
   - Invalid voucher rejection (`INVALID-9999`) verified.
   - Disabled voucher rejection (`68ZK-BN8A`) verified.
   - Single-device simultaneous policy (`shared-users=1`) verified.
   - Operator session disconnect (`/ip hotspot active remove`) verified.
   - Mobile status page rendering (uptime, byte counters, logout) verified.
