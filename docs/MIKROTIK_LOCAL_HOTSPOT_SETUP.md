# MikroTik Local Hotspot & Voucher Lab Setup Guide

**Target Hardware:** MikroTik hAP ac lite (RouterOS 6.49.19 long-term)  
**Operating Model:** Local RouterOS Hotspot User Authentication (No FreeRADIUS)  
**Status:** Step-by-Step Operator Checkpoints  

---

## Architecture Topology Overview

```text
               Upstream Internet
                       │
                 [Airtel Router]
                       │ (Ethernet)
                       ▼
          [MikroTik hAP ac lite (ether1)]
                       │
       ┌───────────────┴───────────────┐
       │                               │
[Management Network]         [Customer Hotspot Network]
  ether2-5 / Bridge            wlan1 / Hotspot Pool
 192.168.88.0/24               10.5.50.0/24
 Admin access allowed          Captive Portal Redirect
```

---

## Checkpoint A — Baseline Capture

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Execute baseline export before modifying settings:

```routeros
/export hide-sensitive file=phase1-baseline
/system backup save name=phase1-baseline
```

**Verification Command:**
```routeros
/file print where name~"phase1-baseline"
```
**Expected Output:** File list showing `phase1-baseline.rsc` and `phase1-baseline.backup`.

---

## Checkpoint B — WAN (Airtel Router on `ether1`)

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Configure `ether1` as WAN interface receiving dynamic IP via DHCP client from upstream Airtel router.

```routeros
# Set interface name
/interface set [ find default-name=ether1 ] name=ether1-WAN comment="Upstream Airtel WAN"

# Add DHCP client on WAN interface
/ip dhcp-client add interface=ether1-WAN disabled=no add-default-route=yes use-peer-dns=yes use-peer-ntp=yes
```

**Verification Commands:**
```routeros
/ip dhcp-client print detail
/ip address print where interface=ether1-WAN
/ping 8.8.8.8 count=3
/ping google.com count=3
```
**Expected State:** `status=bound`, valid WAN IP assigned (e.g. `192.168.1.X/24` or `192.168.0.X/24`), ping to `8.8.8.8` and `google.com` succeeds.  
**Rollback:** `/ip dhcp-client remove [find interface=ether1-WAN]`.

---

## Checkpoint C — Management LAN (`192.168.88.0/24`)

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Preserve management interface bridge (`bridge-mgmt`) on ports `ether2`-`ether5` for administrator access.

```routeros
# Create bridge for management
/interface bridge add name=bridge-mgmt comment="Local Admin Management LAN"

# Add ether2-ether5 to management bridge
/interface bridge port add bridge=bridge-mgmt interface=ether2
/interface bridge port add bridge=bridge-mgmt interface=ether3
/interface bridge port add bridge=bridge-mgmt interface=ether4
/interface bridge port add bridge=bridge-mgmt interface=ether5

# Assign static management IP
/ip address add address=192.168.88.1/24 interface=bridge-mgmt comment="Management IP"
```

**Verification Commands:**
```routeros
/interface bridge print detail
/ip address print where interface=bridge-mgmt
```
**Expected State:** `192.168.88.1/24` assigned on `bridge-mgmt`.

---

## Checkpoint D — Customer Hotspot Network (`10.5.50.0/24`)

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Establish isolated network addressing for hotspot customers on `wlan1` separate from management network.

```routeros
# Assign IP pool for Hotspot
/ip pool add name=hs-pool-10.5.50.0 ranges=10.5.50.10-10.5.50.254

# Assign gateway IP address on wlan1
/ip address add address=10.5.50.1/24 interface=wlan1 comment="Hotspot Customer Gateway"
```

**Verification Command:**
```routeros
/ip address print where interface=wlan1
/ip pool print where name=hs-pool-10.5.50.0
```
**Expected State:** `10.5.50.1/24` assigned to `wlan1`. Pool `hs-pool-10.5.50.0` created (`10.5.50.10-10.5.50.254`).

---

## Checkpoint E — Wi-Fi (`Usimamizi-WiFi-Lab`)

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Configure `wlan1` wireless interface for open hotspot connection.

```routeros
# Configure wireless mode and SSID
/interface wireless set [ find default-name=wlan1 ] \
    mode=ap-bridge \
    ssid="Usimamizi-WiFi-Lab" \
    frequency=auto \
    band=2ghz-b/g/n \
    wireless-protocol=802.11 \
    security-profile=default \
    disabled=no \
    comment="Phase 1 Lab Hotspot Wi-Fi"
```

**Verification Command:**
```routeros
/interface wireless print detail
```
**Expected State:** `wlan1` enabled in `ap-bridge` mode with SSID `"Usimamizi-WiFi-Lab"`.

---

## Checkpoint F — DHCP, DNS & NAT

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Set up DHCP server for hotspot clients, DNS server, and NAT masquerade for internet access.

```routeros
# Enable DNS server with remote requests allowed
/ip dns set allow-remote-requests=yes servers=8.8.8.8,1.1.1.1

# Configure DHCP server on wlan1
/ip dhcp-server add name=dhcp-hotspot interface=wlan1 address-pool=hs-pool-10.5.50.0 disabled=no

# Configure DHCP network parameters
/ip dhcp-server network add address=10.5.50.0/24 gateway=10.5.50.1 dns-server=10.5.50.1 comment="Hotspot Customer Network"

# Configure NAT masquerade rule for WAN egress
/ip firewall nat add chain=srcnat out-interface=ether1-WAN action=masquerade comment="Masquerade Hotspot Outgoing Traffic"
```

**Verification Commands:**
```routeros
/ip dhcp-server print detail
/ip firewall nat print detail
```
**Expected State:** DHCP server `dhcp-hotspot` active on `wlan1`. NAT masquerade active for `ether1-WAN`.

---

## Checkpoint G — HotSpot Service Setup

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Initialize RouterOS HotSpot server on `wlan1`.

```routeros
# Create Hotspot server profile
/ip hotspot profile add name=hsprof1 \
    hotspot-address=10.5.50.1 \
    dns-name="login.usimamizi.lab" \
    html-directory=hotspot \
    login-by=http-chap,http-pap,cookie,mac-cookie \
    mac-auth-password="" \
    split-user-domain=no

# Create Hotspot instance
/ip hotspot add name=hotspot1 \
    interface=wlan1 \
    address-pool=hs-pool-10.5.50.0 \
    profile=hsprof1 \
    disabled=no
```

**Verification Commands:**
```routeros
/ip hotspot print detail
/ip hotspot profile print detail
```
**Expected State:** `hotspot1` active on `wlan1`, DNS name `login.usimamizi.lab`.

---

## Checkpoint H — Voucher User Profiles

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Create local technical user profiles for lab testing: `LAB-15MIN`, `LAB-1H`, `LAB-DAY`.

```routeros
# Profile 1: LAB-15MIN (15 minutes, 2M/5M rate limit, 1 device)
/ip hotspot user profile add name=LAB-15MIN \
    session-timeout=15m \
    idle-timeout=5m \
    keepalive-timeout=2m \
    rate-limit="2M/5M" \
    shared-users=1 \
    transparent-proxy=no \
    on-login=""

# Profile 2: LAB-1H (1 hour, 3M/10M rate limit, 1 device)
/ip hotspot user profile add name=LAB-1H \
    session-timeout=1h \
    idle-timeout=10m \
    keepalive-timeout=2m \
    rate-limit="3M/10M" \
    shared-users=1 \
    transparent-proxy=no

# Profile 3: LAB-DAY (24 hours, 5M/15M rate limit, 1 device)
/ip hotspot user profile add name=LAB-DAY \
    session-timeout=24h \
    idle-timeout=15m \
    keepalive-timeout=2m \
    rate-limit="5M/15M" \
    shared-users=1 \
    transparent-proxy=no
```

**Verification Command:**
```routeros
/ip hotspot user profile print detail
```
**Expected State:** 3 profiles configured with specified rate limits and session timeouts.

---

## Checkpoint I — Captive Portal Deployment

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

Deploy custom low-bandwidth HTML/CSS captive portal files from `infrastructure/mikrotik/hotspot-portal/` to RouterOS flash directory `/hotspot/`.

1. Open WinBox -> **Files**.
2. Drag and drop `login.html`, `status.html`, `logout.html`, `errors.html`, and `style.css` into the `/hotspot` folder on the router.

**Verification Command:**
```routeros
/file print where name~"hotspot"
```

---

## Checkpoint J — Verification & Active Sessions

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**

1. Connect test phone/laptop to Wi-Fi `Usimamizi-WiFi-Lab`.
2. Verify captive portal popup opens `login.usimamizi.lab`.
3. Generate voucher code using `python scripts/mikrotik/generate_vouchers.py --profile LAB-15MIN --count 1`.
4. Import generated `/ip hotspot user add ...` command into RouterOS terminal.
5. Enter voucher code on captive portal and click **Connect**.
6. Verify active session in RouterOS:

```routeros
/ip hotspot active print detail
```

**Disconnect Session Command:**
```routeros
/ip hotspot active remove [find user="VOUCHER_CODE"]
```
