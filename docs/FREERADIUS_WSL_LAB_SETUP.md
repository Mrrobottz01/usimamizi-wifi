# FreeRADIUS 3.2.8 WSL Lab Setup & AAA Integration Guide

Documentation and runbook for running **FreeRADIUS 3.2.8** under WSL Ubuntu connected to **Django AAA Control Plane** and **MikroTik RouterOS 6.49.19** (Usimamizi Wi-Fi).

---

## 1. Physical Lab Architecture

```text
       ┌───────────────────────────────┐
       │   Customer Phone / Laptop     │
       └──────────────┬────────────────┘
                      │ Wi-Fi Association (SSID: Usimamizi-WiFi-Lab)
                      ▼
       ┌───────────────────────────────┐
       │   MikroTik hAP ac lite Router │
       │   IP: 10.5.50.1               │
       │   HotSpot: hotspot1           │
       │   CoA Port: UDP 3799 (RFC3576)│
       └───────┬───────────────▲───────┘
               │               │
  Access-Req   │ UDP 1812      │ Disconnect-Request
  Accounting   │ UDP 1813      │ UDP 3799
               ▼               │
       ┌───────────────────────┴───────┐
       │   WSL Ubuntu FreeRADIUS 3.2.8 │
       │   Host IP: 10.5.50.254        │
       │   Module: rlm_rest            │
       └──────────────┬────────────────┘
                      │ REST JSON API (HTTP POST)
                      │ Port: 8000 (localhost mirroring)
                      ▼
       ┌───────────────────────────────┐
       │   Django Central AAA Backend  │
       │   http://127.0.0.1:8000       │
       │   - /api/v1/radius/authorize/ │
       │   - /api/v1/radius/accounting/│
       └───────────────────────────────┘
```

---

## 2. Configuration Files & Roles

| Path | Purpose |
| :--- | :--- |
| `infrastructure/freeradius/mods-available/rest` | FreeRADIUS `rlm_rest` module config routing requests to Django. |
| `infrastructure/freeradius/sites-available/default` | FreeRADIUS virtual server policy delegating authorization & accounting to `rest`. |
| `infrastructure/freeradius/clients.conf` | NAS router registration (`10.5.50.1`, `nastype = mikrotik`, `require_message_authenticator = true`). |
| `scripts/freeradius/install_wsl_freeradius.sh` | Automated deployment script to install packages, backup originals, deploy configs, and validate. |

---

## 3. Automated Lab Deployment

Run the automated script inside WSL Ubuntu as root:

```bash
sudo bash /mnt/c/Users/fsociety/Documents/Usimamizi-wifi/scripts/freeradius/install_wsl_freeradius.sh
```

The script automatically:
1. Installs `freeradius`, `freeradius-rest`, and `freeradius-utils`.
2. Preserves stock configurations with `.orig` backups.
3. Links `mods-available/rest` to `mods-enabled/rest`.
4. Deploys updated `clients.conf` and `sites-available/default`.
5. Validates syntax using `freeradius -XC`.
6. Restarts `freeradius.service`.

---

## 4. BlastRADIUS Security Hardening

To mitigate the BlastRADIUS vulnerability (CVE-2024-3596):
- `clients.conf` specifies `require_message_authenticator = true` for the MikroTik client (`10.5.50.1`).
- All Access-Request packets must include the RADIUS `Message-Authenticator` attribute (RouterOS 6.49.19 sends this by default).
- Unauthenticated or forged packets missing `Message-Authenticator` are immediately dropped.

---

## 5. Machine-to-Machine API Security (`X-RADIUS-API-KEY`)

- **Development / Lab Environment:** `RADIUS_API_SECRET` is unset in development settings, permitting local AAA communication without extra headers.
- **Production Environment:** Set `RADIUS_API_SECRET` in `.env` and configure FreeRADIUS with:
  ```unlang
  update control {
      &REST-HTTP-Header := "X-RADIUS-API-KEY: <SECRET>"
  }
  ```
  Django strictly enforces HTTP 403 when `RADIUS_API_SECRET` is set and the header is missing or mismatched.
