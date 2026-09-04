# Voucher Management Architecture & Lifecycle

## 1. Overview

The Usimamizi Wi-Fi platform provides enterprise-grade, multi-tenant voucher management for internet access monetization across hospitality venues, ISP hotspots, retail locations, and rural connectivity deployments.

Vouchers represent cryptographic, one-time or reusable access keys that authenticate end-user devices against central FreeRADIUS AAA servers while mapping to strict billing, bandwidth, and session constraints.

---

## 2. Multi-Tenant Batch & Voucher Architecture

### 2.1 Domain Hierarchy

```
Company (Tenant)
 ├── HotspotConfiguration (Captive Portal SSID & Branding)
 ├── Plans (Pricing, Speeds, Quotas, Device Limits)
 └── VoucherBatch
      ├── Reference: VB-YYYYMMDD-XXXXXX
      ├── Distribution Mode: CENTRAL_SAAS | LOCAL_FALLBACK
      ├── Export Status: NOT_EXPORTED | EXPORTED_ROUTEROS
      ├── Metadata: label, notes, created_by
      └── Vouchers (1 .. 5,000 per batch)
           ├── Display Code: ABCD-EFGH (canonical uppercase, hyphenated)
           ├── Code Hash: SHA-256 (for ultra-fast O(1) indexed lookup)
           ├── Status: AVAILABLE | RESERVED | REDEEMED | EXPIRED | REVOKED
           ├── Distribution State: UNSOLD | SOLD | GIVEN_FREE | PROMOTIONAL | INTERNAL_TEST
           ├── Export Status: NOT_EXPORTED | EXPORTED_ROUTEROS
           ├── Recipient Phone: E.164 normalized mobile (+255...)
           └── AccessEntitlement: 1-to-1 linkage upon first activation
```

---

## 3. Strict State Machine & Lifecycle Transitions

Vouchers enforce strict lifecycle invariants:

| Current State | Permitted Next States | Trigger Event / Policy |
| :--- | :--- | :--- |
| **AVAILABLE** | `RESERVED`, `REDEEMED`, `REVOKED`, `EXPIRED` | Allocated to customer, portal redemption, admin cancellation, or validity timeout. |
| **RESERVED** | `REDEEMED`, `REVOKED`, `EXPIRED` | Customer logs into portal, admin cancellation, or validity timeout. |
| **REDEEMED** | `REVOKED`, `EXPIRED` | Admin revokes voucher (triggers RFC 3576 POD disconnect) or plan usage exhausts. |
| **REVOKED** | *Terminal State* | No transitions allowed. Re-authentication immediately rejected. |
| **EXPIRED** | *Terminal State* | No transitions allowed. Access blocked. |

### Invariant Rules:
1. **No Double Redemption**: An `AVAILABLE` or `RESERVED` voucher transitions to `REDEEMED` atomically using a database row lock (`select_for_update()`).
2. **Cascading Revocation**: Revoking a `REDEEMED` voucher automatically transitions its associated `AccessEntitlement` to `REVOKED` and fires RFC 3576 Disconnect-Requests to the NAS router.
3. **Tenant Isolation**: Every query and operation scopes through `company_id`. Cross-tenant voucher redemptions are rejected at the service and selector layers.

---

## 4. Code Normalization & Formatting

To ensure friction-free input on mobile keyboards, voucher codes are normalized using canonical rules:

1. Strip whitespace, dashes, and special symbols: `abcd 7xq9` -> `ABCD7XQ9`
2. Uppercase all alphanumeric characters.
3. Format as standard 4-character chunks: `ABCD-7XQ9`.
4. Store SHA-256 hash for secure matching without plain-text vulnerability.

---

## 5. Distribution Modes

- **Central SaaS (`CENTRAL_SAAS`)**: Primary mode. Vouchers authenticate directly through FreeRADIUS REST hooks with real-time accounting, bandwidth shaping (`Mikrotik-Rate-Limit`), and RFC 3576 session termination.
- **Local Fallback (`LOCAL_FALLBACK`)**: Offline emergency mode. Vouchers are exported into MikroTik RouterOS scripts (`.rsc`) for pre-population in `/ip hotspot user`. Used when central cloud uplink is severed.

---

## 6. Real-Time Dashboard Metrics

The Voucher Hub aggregates real-time operational metrics per tenant:
- **Total Vouchers Generated**
- **Available vs. Reserved vs. Redeemed vs. Revoked**
- **Distribution States** (Sold, Given Free, Unsold)
- **SMS Dispatches** (RafikiSMS integration)
- **RouterOS Exports** (Offline synchronization badge)
- **Redemption Conversion Rate (%)**
