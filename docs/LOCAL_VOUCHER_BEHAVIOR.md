# Local RouterOS Voucher Enforcement & Behavioral Mechanics

**System Name:** Usimamizi Wi-Fi  
**Phase:** Phase 1 — Local MikroTik Hotspot Lab  
**RouterOS Version:** 6.49.19  

---

## 1. Executive Summary

This document specifies how local RouterOS 6 Hotspot user properties enforce access limits and how these local mechanisms map to future SaaS domain entities (`Entitlement`, `Session`, `RADIUS`).

---

## 2. RouterOS 6 Time Limits & Validity Semantics

RouterOS 6 provides distinct parameters for controlling user access duration. It is critical not to confuse these parameters:

| Parameter | RouterOS Field | Lab Enforcement Behavior | Mapping to Future SaaS Model |
| :--- | :--- | :--- | :--- |
| **Session Timeout** | `session-timeout` | Maximum continuous time allowed for **one single connection session**. Once reached, session disconnects. | Maps to maximum continuous RADIUS session length (`Session-Timeout`). |
| **Uptime Limit** | `limit-uptime` | Cumulative online time consumed across multiple sessions until voucher is exhausted. | Maps to `Entitlement.allowed_seconds` / `used_seconds`. |
| **Idle Timeout** | `idle-timeout` | Duration of inactivity (no traffic) before user is automatically logged out to release pool IP. | Maps to RADIUS `Idle-Timeout` attribute. |
| **Calendar Expiry** | *Not natively enforced in local RouterOS user model without scripts* | Local RouterOS users do not expire at midnight or on a specific calendar date automatically. | Handled natively by SaaS backend entitlement engine (`expires_at`). |

---

## 3. One-Device Policy (`shared-users=1`)

In local RouterOS Hotspot configuration, setting `shared-users=1` on `/ip hotspot user profile` enforces single-device usage:

### Simultaneous Login Behavior:
- **Device 1** connects with voucher `K7PM-4XQ9` -> Authentication succeeds.
- **Device 2** attempts login with same voucher `K7PM-4XQ9` while Device 1 is active -> **Login Rejected** by RouterOS with error *"no more sessions allowed for user"*.

### Sequential Device Transfer Behavior:
- If Device 1 disconnects (or is removed from `/ip hotspot active`), Device 2 can authenticate using the same voucher unless `mac-cookie` or MAC locking is enabled.
- **Conclusion:** Local RouterOS `shared-users=1` enforces **simultaneous session limits**, not permanent hardware MAC lock-in. Permanent MAC binding requires explicit SaaS device tracking (`Device` model).

---

## 4. Cookie & MAC Cookie Mechanics

RouterOS Hotspot profile supports `cookie` and `mac-cookie` login methods:

```routeros
login-by=http-chap,http-pap,cookie,mac-cookie
```

- **HTTP Cookie:** Browser stores a session cookie (`DST` / `CHAP`). Re-opening browser auto-logs in without re-entering voucher.
- **MAC Cookie:** Router remembers the device MAC address (`/ip hotspot cookie`). When Wi-Fi disconnects and reconnects, device bypasses captive portal automatically until cookie lifetime expires.
- **Side Effect:** If a user wants to switch devices, they must wait for the MAC cookie to expire or explicit operator removal (`/ip hotspot cookie remove`).

---

## 5. Disconnect vs Revocation

| Operation | RouterOS Command | Effect on Voucher |
| :--- | :--- | :--- |
| **Disconnect Session** | `/ip hotspot active remove [find user="CODE"]` | Terminates active connection. Remaining time on voucher is **preserved**. User can re-login. |
| **Revoke Voucher** | `/ip hotspot user disable [find name="CODE"]` | Disables user account. User **cannot** re-login. Time remaining is locked out. |
| **Delete Voucher** | `/ip hotspot user remove [find name="CODE"]` | Permanently deletes user account from router database. |

---

## 6. Mapping Matrix: Local RouterOS -> SaaS Architecture

| Local RouterOS Concept | SaaS Platform Equivalent |
| :--- | :--- |
| `/ip hotspot user` | `Voucher` + `Entitlement` |
| `/ip hotspot active` | `Session` |
| `/ip hotspot user profile` | `Plan` |
| `rate-limit="2M/5M"` | `Plan.upload_speed` / `Plan.download_speed` (WISPr attributes) |
| `limit-uptime=1h` | `Entitlement.allowed_seconds = 3600` |
