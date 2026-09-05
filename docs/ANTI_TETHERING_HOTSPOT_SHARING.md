# Anti-Tethering & Wi-Fi HotSpot Sharing Prevention

## Overview
By default, some smartphones (specifically modern Android devices and Windows laptops with "Wi-Fi Sharing / Wi-Fi Bridge" enabled) allow a customer who connects to a Wi-Fi HotSpot to broadcast their own private mobile hotspot. This allows their friends to share a single paid voucher without purchasing their own access.

Usimamizi Wi-Fi enforces **strict commercial protection** so that each physical device must possess its own valid voucher or subscription.

---

## Defense-in-Depth Protection Layers

### Layer 1: Central AAA & Simultaneous Session Enforcement
- Every plan has `simultaneous_sessions = 1` and `max_devices = 1`.
- When a voucher is authenticated, FreeRADIUS checks active sessions in `radacct`.
- If a second device attempts to log in using the same voucher code directly on the captive portal, the system returns:
  `DEVICE_LIMIT_REACHED: "This voucher has reached its maximum device limit (1 device)."`

---

### Layer 2: MikroTik TTL Lock (Mangle Postrouting)
When an authorized phone turns on its internal Wi-Fi hotspot and NATs traffic for friends, the phone acts as an intermediate router. Under RFC 791 (IPv4 standard), an intermediate router **must decrement the TTL (Time-To-Live)** field of any forwarded packet by at least 1.

We apply a mangle rule on the MikroTik router that forces all downstream packets destined for hotspot clients to have a TTL of 1:

```routeros
/ip firewall mangle
add chain=postrouting out-interface=bridgeLocal dst-address=!10.5.50.254 action=change-ttl new-ttl=set:1 passthrough=yes comment="Usimamizi: Anti-Tethering (Block Hotspot Sharing)"
```

#### How it works:
1. **Primary Phone (Owner of Voucher):**
   - Packets arriving from the internet reach the phone with `TTL = 1`.
   - Because the phone is the final endpoint, its operating system accepts and processes the packets normally. Internet works 100% smoothly.
2. **Tethered Secondary Devices (Friends):**
   - When the phone receives incoming internet responses intended for tethered friends, the phone's networking stack attempts to forward the packet across its hotspot bridge.
   - Forwarding requires decrementing the TTL: `1 - 1 = 0`.
   - With `TTL = 0`, the phone's operating system discards the packet immediately.
   - **Result:** Secondary devices receive 0 bytes of downstream internet and cannot load any web pages or apps.

---

### Layer 3: Upstream Forward Filter (Drop Forwarded Client Traffic)
To prevent tethered devices from even sending upstream requests or DNS queries into the router, MikroTik drops forwarded client packets arriving with decremented TTLs:

```routeros
/ip firewall filter
add chain=forward in-interface=bridgeLocal ttl=equal:63 action=drop comment="Usimamizi: Anti-Tethering Drop forwarded client packets (TTL 63)"
add chain=forward in-interface=bridgeLocal ttl=equal:127 action=drop comment="Usimamizi: Anti-Tethering Drop forwarded client packets (TTL 127)"
```

- Native Android/iOS/macOS packets originate with `TTL = 64`. Forwarded packets arrive with `TTL = 63` and are instantly dropped.
- Native Windows packets originate with `TTL = 128`. Forwarded packets arrive with `TTL = 127` and are instantly dropped.

---

## Operational Verification

To inspect active rules and dropped packet counters on the MikroTik router via CLI or API:

```routeros
/ip firewall mangle print where comment~"Anti-Tethering"
/ip firewall filter print where comment~"Anti-Tethering"
```
