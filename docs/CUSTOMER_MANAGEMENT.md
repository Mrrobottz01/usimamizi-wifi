# Usimamizi Wi-Fi: Customer Identity & Device Management

## 1. Overview & Objective

The **Customer Identity Layer** provides persistent, cross-session recognition for Wi-Fi consumers returning to tenant networks. Rather than treating users as transient MAC addresses or isolated voucher redemptions, Usimamizi links purchases, session logs, devices, and communication history to a canonical customer record.

Existing FreeRADIUS AAA, `AccessEntitlement`, MikroTik HotSpot, and Voucher systems continue operating without interruption. Customer identity sits above these systems as a persistent relationship layer.

---

## 2. Canonical Identity & Phone Normalization

In the Tanzanian mobile money ecosystem, customer identities are rooted in MSISDNs. Customers enter phone numbers in varied local and international formats.

Usimamizi standardizes every input through `normalize_customer_phone()`:

| Raw Input | Canonical E.164 Result |
|---|---|
| `0712345678` | `+255712345678` |
| `712345678` | `+255712345678` |
| `255712345678` | `+255712345678` |
| `+255712345678` | `+255712345678` |
| `+255 712-345 678` | `+255712345678` |
| `0655123456` | `+255655123456` |

### Multi-Tenant Isolation
- The unique constraint is enforced on `(company_id, normalized_phone)`.
- If a customer connects to Company A and Company B, two completely isolated customer records exist, ensuring complete data privacy and billing separation across tenants.

---

## 3. Device Registration & Randomized MAC Management

Every physical device connecting through captive portal or observed by RADIUS is registered in `CustomerDevice`:

```text
┌─────────────────────────────────────────────────────────────┐
│                       Customer                              │
│              ID: 3a9f0e... | +255712345678                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ 1-to-Many
                               ▼
 ┌─────────────────────────────┬─────────────────────────────┐
 │       Device 1              │       Device 2              │
 │ MAC: 82:45:98:C1:B4:98      │ MAC: 54:E1:AD:12:34:56      │
 │ Name: Samsung Galaxy A52    │ Name: ThinkPad Laptop       │
 │ Type: MOBILE                │ Type: LAPTOP                │
 │ Trusted: Yes | Blocked: No  │ Trusted: No  | Blocked: No  │
 └─────────────────────────────┴─────────────────────────────┘
```

### MAC Normalization
- All hardware addresses are canonicalized to standard uppercase hyphenless colon format: `AA:BB:CC:DD:EE:FF`.
- If modern devices use randomized private MACs per Wi-Fi network, the device record automatically updates its `last_seen_at` without duplicating identities.

### Device Trust & Blocking
- **Trusted Device:** Bypass captive portal prompt when MAC-auth is enabled.
- **Blocked Device:** Rejected at FreeRADIUS authorization level regardless of valid voucher or active entitlement.

---

## 4. Lifecycle Status Transitions

A customer profile moves through four states:

1. **`ACTIVE`**: Full service access. Authorized to browse and renew plans.
2. **`SUSPENDED`**: Access temporarily frozen by administrator. Active entitlements are revoked, and real-time RFC 3576 POD Disconnect-Requests are immediately sent to the router.
3. **`BLOCKED`**: Permanently barred from portal access and OTP generation due to fraud or TOS violation.
4. **`ARCHIVED`**: Retained for audit and revenue compliance but hidden from day-to-day active dashboards.

---

## 5. API Reference

### Admin Endpoints
- `GET /api/v1/customers/?company_id={id}&q={search}&status={status}`: Search and list customers with total spent, active subscription info, and metrics.
- `GET /api/v1/customers/{id}/`: Customer detail profile.
- `POST /api/v1/customers/{id}/suspend/`: Suspend customer and drop sessions.
- `POST /api/v1/customers/{id}/reactivate/`: Restore customer status.
- `POST /api/v1/customers/{id}/block/`: Block customer permanently.
- `GET /api/v1/customers/{id}/devices/`: List customer devices.
- `POST /api/v1/customers/{id}/devices/{device_id}/toggle-trust/`: Toggle trust flag.
- `POST /api/v1/customers/{id}/devices/{device_id}/toggle-block/`: Toggle hardware block.
- `GET /api/v1/customers/{id}/timeline/`: Unified activity stream combining payments, sessions, SMS alerts, and subscription events.
