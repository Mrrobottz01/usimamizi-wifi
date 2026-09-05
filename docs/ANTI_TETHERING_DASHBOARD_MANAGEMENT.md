# Anti-Tethering Dashboard Management & RouterOS Policy Control

## Overview
This document describes the tenant-aware, auditable dashboard feature for managing **Anti-Tethering and Wi-Fi HotSpot Sharing Prevention** in Usimamizi Wi-Fi.

Operators can configure, audit, and synchronize firewall rules directly from the web interface without manually accessing Winbox or the RouterOS CLI:
```text
Settings → HotSpot & Protection → Anti-Tethering & Router Policy
```

---

## 1. Multi-Layer Protection Architecture

The anti-tethering subsystem combines three defense-in-depth layers:

```text
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Central AAA & Commercial Boundary (FreeRADIUS)    │
│  - max_devices = 1                                         │
│  - simultaneous_sessions = 1                               │
│  - Blocks secondary logins on the captive portal            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: IPv4 Downstream TTL Lock (MikroTik Mangle)        │
│  - chain=postrouting out-interface=bridgeLocal             │
│  - action=change-ttl new-ttl=set:1                         │
│  - Phone receives TTL=1. Forwarded packets reach TTL=0     │
│  - Secondary tethered devices receive 0 bytes downstream   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Forwarded Client Detection (MikroTik Filter)       │
│  - chain=forward in-interface=bridgeLocal ttl=equal:63 drop│
│  - chain=forward in-interface=bridgeLocal ttl=equal:127 drop│
│  - Drops forwarded upstream requests from Android/iOS/Win   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. RouterOS Rule Identifiers & Legacy Adoption

To ensure idempotence and prevent duplicate rules across repeated sync operations, Usimamizi assigns canonical comment identifiers:

| Rule Type | Table | Canonical Tag | Legacy Adoption Markers |
| :--- | :--- | :--- | :--- |
| **TTL Lock** | `/ip/firewall/mangle` | `USIMAMIZI_ANTI_TETHER_TTL_LOCK` | `Anti-Tethering (Block Hotspot Sharing)`, `Anti-Tethering` |
| **TTL 63 Drop** | `/ip/firewall/filter` | `USIMAMIZI_ANTI_TETHER_TTL63` | `Anti-Tethering Drop forwarded client packets (TTL 63)`, `TTL 63` |
| **TTL 127 Drop** | `/ip/firewall/filter` | `USIMAMIZI_ANTI_TETHER_TTL127` | `Anti-Tethering Drop forwarded client packets (TTL 127)`, `TTL 127` |

### Legacy Adoption Logic
When the synchronization service encounters existing rules with legacy comments, it automatically adopts them, standardizes the comment tags, and manages them going forward without recreating or duplicating rules. Unrelated firewall rules are never modified or removed.

---

## 3. Data Model (`AntiTetheringPolicy`)

```python
class AntiTetheringPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='anti_tethering_policies')
    hotspot = models.OneToOneField(HotspotConfiguration, on_delete=models.CASCADE, related_name='anti_tethering_policy')
    
    enabled = models.BooleanField(default=True)
    max_devices = models.PositiveIntegerField(default=1)
    simultaneous_sessions = models.PositiveIntegerField(default=1)
    
    ttl_lock_enabled = models.BooleanField(default=True)
    ttl_lock_value = models.PositiveIntegerField(default=1)
    
    detect_ttl_63 = models.BooleanField(default=True)
    detect_ttl_127 = models.BooleanField(default=True)
    
    strict_mode = models.BooleanField(default=False)
    ipv6_policy = models.CharField(max_length=32, choices=IPv6Policy.choices, default=IPv6Policy.DISABLED)
    
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_router_status = models.JSONField(default=dict, blank=True)
```

---

## 4. API Endpoints

All endpoints are scoped by tenant company and require authenticated access (`IsCompanyMember`):

- `GET /api/v1/hotspots/{hotspot_id}/anti-tethering/`
  Returns current policy configuration along with live RouterOS status.
- `PATCH /api/v1/hotspots/{hotspot_id}/anti-tethering/?sync=true`
  Updates policy options and triggers immediate router synchronization.
- `POST /api/v1/hotspots/{hotspot_id}/anti-tethering/sync/`
  Forces a reconciliation between SaaS policy and RouterOS firewall rules.
- `GET /api/v1/hotspots/{hotspot_id}/anti-tethering/status/`
  Returns live router status (`ACTIVE`, `PARTIALLY_ACTIVE`, `DISABLED`, `OUT_OF_SYNC`, `ROUTER_UNREACHABLE`).
- `GET /api/v1/hotspots/{hotspot_id}/anti-tethering/counters/`
  Queries RouterOS live and returns packet and byte counters for each managed rule.
- `POST /api/v1/hotspots/{hotspot_id}/anti-tethering/restore-defaults/`
  Resets policy to recommended baseline settings and synchronizes to RouterOS.

---

## 5. Audit Logging

Every policy modification and synchronization event is recorded in `audit_logs`:
- `ANTI_TETHERING_POLICY_UPDATED` (captures `before` and `after` snapshots)
- `ANTI_TETHERING_SYNCED` (captures live status and sync result)
- `ANTI_TETHERING_SYNC_FAILED` (captures error details without exposing credentials)
- `ANTI_TETHERING_DEFAULTS_RESTORED`

---

## 6. Known Scope & Limitations

1. **IPv6:** IPv4 is currently standard on HotSpot captive portals. IPv6 anti-tethering is labeled `NOT CONFIGURED` to avoid false security claims.
2. **Encrypted VPN / Tunneling:** If a client routes tethered traffic through an encrypted VPN tunnel (WireGuard/OpenVPN/IPsec) running on the primary phone, inner payload TTLs are encapsulated. Specialized Deep Packet Inspection (DPI) or VPN port blocking is required for such edge cases.
