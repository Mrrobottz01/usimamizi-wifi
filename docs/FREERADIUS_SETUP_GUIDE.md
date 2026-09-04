# FreeRADIUS & Central AAA Setup Guide

**System Name:** Usimamizi Wi-Fi  
**Document Status:** Complete Phase 2 Integration Guide  
**Applies To:** FreeRADIUS 3.x, Django REST API (`apps.radius`), MikroTik RouterOS RADIUS Client  

---

## 1. Overview & Architecture

FreeRADIUS acts as the central AAA daemon mediating connection authorization and accounting between MikroTik NAS routers and the SaaS PostgreSQL database:

```text
  [MikroTik RouterOS]
          │ RADIUS Access-Request (UDP 1812) / Accounting (UDP 1813)
          ▼
   [FreeRADIUS Server]
          │ HTTP REST JSON (`rlm_rest`)
          ▼
[Django REST API (/api/v1/radius/)]
          │ ORM
          ▼
[SaaS Database (PostgreSQL)]
```

---

## 2. FreeRADIUS Server Installation

### Docker Setup (Recommended)
```bash
docker run -d --name usimamizi_freeradius \
  -p 1812:1812/udp -p 1813:1813/udp \
  -v $(pwd)/infrastructure/freeradius/clients.conf:/etc/freeradius/clients.conf \
  -v $(pwd)/infrastructure/freeradius/mods-available/rest:/etc/freeradius/mods-available/rest \
  -v $(pwd)/infrastructure/freeradius/sites-available/default:/etc/freeradius/sites-available/default \
  freeradius/freeradius-server:latest
```

---

## 3. RouterOS RADIUS Client Configuration

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**  
> Run the following commands on the lab MikroTik router to configure RADIUS client pointing to FreeRADIUS:

```routeros
# Add FreeRADIUS AAA Server
/radius add service=hotspot \
    address=192.168.88.250 \
    secret="radius_shared_secret_lab" \
    authentication-port=1812 \
    accounting-port=1813 \
    timeout=3000ms \
    comment="Central SaaS FreeRADIUS"

# Enable RADIUS Authentication on HotSpot Profile
/ip hotspot profile set [ find name=hsprof1 ] \
    use-radius=yes \
    radius-mac-format=XX:XX:XX:XX:XX:XX \
    radius-accounting=yes \
    radius-interim-update=1m
```

---

## 4. Verification Commands

### Test RADIUS Access-Request via radtest
```bash
radtest radius_user@example.com ValidPassword123! 127.0.0.1 1812 testing123
```
**Expected Output:** `Received Access-Accept` containing `Mikrotik-Rate-Limit = "3M/10M"` and `Session-Timeout = 3600`.
