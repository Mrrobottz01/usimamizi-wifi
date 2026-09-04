# Plans and Vouchers Architecture Specification

This document details the commercial access control architecture for **Usimamizi Wi-Fi** Plans and Voucher Batches.

## 1. Internet Access Plans (`apps.plans`)

Plans define the commercial and technical constraints governing internet access.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `name` | String | Commercial name (e.g. `1 Hour Pass`) |
| `code` | String | Unique plan code (e.g. `LAB-1H`) |
| `price` | Decimal(12, 2) | Price in local currency (e.g. `1000.00 TZS`) |
| `duration_value` | Integer | Duration quantity |
| `duration_unit` | TextChoice | `HOURS`, `DAYS`, `WEEKS`, `MONTHS` |
| `validity_mode` | TextChoice | `CONTINUOUS`, `USAGE_TIME`, `CALENDAR` |
| `download_speed_kbps` | Integer | Rate limit in Kbps |
| `upload_speed_kbps` | Integer | Upload rate limit in Kbps |
| `max_devices` | Integer | Simultaneous device allowance |

---

## 2. Voucher Batches & Voucher Lifecycle (`apps.vouchers`)

### Voucher Character Set & Security
- Voucher codes are generated using cryptographically secure randomness (`secrets.choice`).
- Character set excludes ambiguous characters: `0`, `O`, `1`, `I`, `L`.
- Formatted as `K7PM-4XQ9`.
- Lookups match display code or SHA-256 `code_hash`.

### Lifecycle States
1. `AVAILABLE`: Ready for customer redemption.
2. `REDEEMED`: Claimed by customer.
3. `EXPIRED`: Reached issuance validity threshold.
4. `REVOKED`: Cancelled by operator with audit trail.

### Concurrency Protection
Redemption executes inside `transaction.atomic()` with `select_for_update()`, guaranteeing that two concurrent redemption requests result in exactly **1 success** and **1 failure**.
