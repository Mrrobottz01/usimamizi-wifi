# MikroTik RouterOS 6 RADIUS HotSpot Setup Guide

Exact RouterOS configuration commands to connect MikroTik HotSpot to the Central FreeRADIUS AAA Server.

---

## 1. Network Topology Overview

```text
                     FreeRADIUS Host
                   <FREERADIUS_SERVER_IP> (e.g. 192.168.1.163)
                             ▲
                             │ UDP 1812 (Auth) / UDP 1813 (Acct)
                             │
Internet ──► Airtel Router ──► MikroTik (ether1: 192.168.1.109)
(192.168.1.1)                 │
                              ▼
                     HotSpot (wlan1: 10.5.50.1)
                              │
                              ▼
                     SSID: Usimamizi-WiFi-Lab
```

---

## 2. RouterOS RADIUS Configuration Commands

Execute in MikroTik Terminal:

```routeros
# 1. Add RADIUS Client for HotSpot service pointing to FreeRADIUS Server IP
/radius add \
    service=hotspot \
    address=<FREERADIUS_SERVER_IP> \
    secret="<LAB_RADIUS_SHARED_SECRET>" \
    authentication-port=1812 \
    accounting-port=1813 \
    timeout=3000ms \
    comment="Usimamizi SaaS Central AAA"

# 2. Enable RADIUS on HotSpot Server Profile
/ip hotspot profile set [find] use-radius=yes radius-accounting=yes radius-interim-update=60s

# 3. Verify Radius Connection & Status
/radius print detail
```

*Replace `<FREERADIUS_SERVER_IP>` with your host machine IP (e.g. `192.168.1.163` or your production FreeRADIUS IP) and `<LAB_RADIUS_SHARED_SECRET>` with your configured shared secret.*
