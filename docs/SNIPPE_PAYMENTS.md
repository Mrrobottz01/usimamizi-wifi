# Snippe Mobile Money & Self-Service Wi-Fi Access Purchase

## Overview

The Usimamizi Wi-Fi Snippe integration enables customers connected to an unauthenticated HotSpot to purchase internet access packages directly from the captive portal using Tanzanian Mobile Money (M-Pesa, Airtel Money, Mixx by Yas, HaloPesa / Halotel).

```
Customer Connects to Wi-Fi
           ↓
Captive Portal (Walled Garden)
           ↓
Selects Package & Enters Phone (+255...)
           ↓
POST /api/v1/public/hotspots/{slug}/purchases/
           ↓
Backend calls Snippe Direct Mobile Money API (POST /v1/payments)
           ↓
Customer receives USSD PIN Prompt on mobile handset
           ↓
Customer enters Mobile Money PIN
           ↓
Snippe dispatches cryptographically signed webhook (POST /api/v1/payments/snippe/webhook/)
           ↓
HMAC-SHA256 Signature Verified with timestamp tolerance (<= 300s)
           ↓
Atomic AccessEntitlement created (source_type = PAYMENT)
           ↓
Attached 8-character human-friendly Voucher generated (XXXX-YYYY)
           ↓
Confirmation SMS dispatched to customer phone (failure-isolated)
           ↓
Captive Portal polling detects FULFILLED status
           ↓
Automatic RouterOS Login Handoff (/login POST)
           ↓
Customer gains instant high-speed Internet access!
```

---

## 1. Security Principles

1. **Frontend Success Never Grants Access:**
   Only a verified `payment.completed` webhook from Snippe (or a verified backend status reconciliation check) can finalize a purchase and provision an `AccessEntitlement`.
2. **HMAC-SHA256 Webhook Verification:**
   All inbound webhook payloads are cryptographically checked using constant-time comparison (`hmac.compare_digest`) against the tenant or platform's `SNIPPE_WEBHOOK_SECRET`.
3. **Timestamp Tolerance & Replay Protection:**
   Webhooks verify the `X-Webhook-Timestamp` header is within $\pm 300$ seconds of server time. Processed `event_id` records in `PaymentWebhookEvent` prevent duplicate entitlement generation.
4. **Credential Encryption at Rest:**
   Tenant gateway credentials (`api_key`, `webhook_secret`) are encrypted at rest using Fernet symmetric encryption and masked (`••••••••`) on API responses.
5. **Idempotency Key Enforcement:**
   Snippe strictly requires `Idempotency-Key` $\le 30$ characters. Keys are deterministically bounded (e.g. `idmp_` + 24-char hex = 29 characters).

---

## 2. Data Models (`apps/payments/models.py`)

| Model | Purpose | Key Fields |
|---|---|---|
| `PaymentProviderConfiguration` | Tenant credentials & environment settings | `company`, `provider` (SNIPPE), `environment` (sandbox/live), `api_key_encrypted`, `webhook_secret_encrypted` |
| `AccessPurchase` | High-level commercial access order | `company`, `hotspot`, `plan`, `reference` (`PUR-YYYYMMDD-XXXXXX`), `customer_phone`, `amount`, `status` (`CREATED`, `PAYMENT_PENDING`, `FULFILLED`, `FAILED`), `entitlement`, `voucher` |
| `PaymentTransaction` | Financial ledger transaction | `purchase`, `internal_reference` (`TXN-YYYYMMDD-XXXXXX`), `provider_reference`, `amount`, `status` (`PENDING`, `COMPLETED`, `FAILED`), `checkout_url` |
| `PaymentAttempt` | Outbound API call idempotency log | `transaction`, `idempotency_key`, `request_payload`, `response_payload`, `status_code` |
| `PaymentWebhookEvent` | Inbound audit trail & deduplication | `provider`, `event_id`, `event_type`, `signature`, `payload`, `is_processed`, `processed_at` |
| `HotspotWalledGardenEntry` | Pre-auth allowlist rules | `company`, `hotspot`, `entry_type` (`DOMAIN`, `IP`), `host`, `address`, `purpose` (`PAYMENT`, `PORTAL`, `SYSTEM`) |

---

## 3. MikroTik HotSpot Walled Garden Configuration

Unauthenticated customers must be able to reach Snippe API and web endpoints without internet access.

### 1-Click Allowlist Presets

1. **Snippe Payments:**
   - `api.snippe.sh`
   - `snippe.sh`
   - `snippe.me`
2. **Usimamizi Portal:**
   - `10.5.50.1` (Router HotSpot Gateway)
   - `10.5.50.254` (Server Host)

### RouterOS Synchronization Script

Execute directly on the MikroTik terminal:

```routeros
# --- Domain Walled Garden (HTTP/HTTPS Host Redirection Bypass) ---
/ip hotspot walled-garden add dst-host="api.snippe.sh" comment="Usimamizi: Snippe API gateway"
/ip hotspot walled-garden add dst-host="snippe.sh" comment="Usimamizi: Snippe root domain"
/ip hotspot walled-garden add dst-host="snippe.me" comment="Usimamizi: Snippe checkout domain"

# --- IP/CIDR Walled Garden (L3 Bypass for Portal / Server) ---
/ip hotspot walled-garden ip add dst-address="10.5.50.1" action=accept comment="Usimamizi: HotSpot Gateway"
/ip hotspot walled-garden ip add dst-address="10.5.50.254" action=accept comment="Usimamizi: Portal Server"
```

---

## 4. API Endpoints

### Public Captive Portal Endpoints
- `GET /api/v1/public/hotspots/{slug}/plans/`: Lists active commercial packages with price in TZS.
- `POST /api/v1/public/hotspots/{slug}/purchases/`: Customer initiates mobile money purchase (`plan_id`, `customer_phone`).
- `GET /api/v1/public/purchases/{reference}/status/`: Customer polls purchase fulfillment status.

### Webhook Endpoint
- `POST /api/v1/payments/snippe/webhook/`: Inbound HMAC-verified webhook handler for `payment.completed`, `payment.failed`, `payment.expired`.

### Tenant Admin Endpoints
- `GET /api/v1/payments/?company_id=...`: Lists financial payment transactions.
- `GET /api/v1/payments/purchases/?company_id=...`: Lists customer purchase orders.
- `GET /api/v1/payments/reports/summary/?company_id=...`: Today's and total revenue metrics.
- `GET / PUT /api/v1/payments/settings/?company_id=...`: Configures Snippe API key and webhook secret.
- `GET / POST / DELETE /api/v1/payments/walled-garden/?company_id=...`: Manages walled garden rules.
- `POST /api/v1/payments/walled-garden/presets/apply/?company_id=...`: Applies 1-click allowlist presets.
- `GET /api/v1/payments/walled-garden/export-routeros/?company_id=...`: Exports RouterOS `.rsc` configuration.

---

## 5. Verification Checklist

```text
Backend Test Suite: 95/95 passing
Ruff check: Clean (0 errors)
Database Migrations: Clean (0 missing)
Frontend Typecheck: Clean (0 errors)
Frontend Lint: Clean (0 warnings)
Frontend Build: Clean (Vite production bundle generated)
Frontend Tests: 4/4 passing
```
