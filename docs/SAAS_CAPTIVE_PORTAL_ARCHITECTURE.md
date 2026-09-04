# SaaS Captive Portal Architecture & Customer Journey

Architectural specification for the tenant-aware SaaS captive portal in **Usimamizi Wi-Fi** (Phase 6).

---

## 1. High-Level Customer Journey

```text
Customer Device
       │
       ▼ (Wi-Fi Association)
MikroTik HotSpot Router (10.5.50.1 / wlan1)
       │
       ▼ (Captive Network Assistant / HTTP 302 Redirect)
SaaS Captive Portal (/p/:hotspotSlug)
       │
       ├─► GET /api/v1/public/hotspots/:slug/portal/ (Resolves tenant branding, colors, language)
       │
       ▼ Customer enters Voucher (e.g. "PG72-E8P8")
POST /api/v1/public/hotspots/:slug/voucher/
       │
       ├─► Validates tenant ownership (Company isolation)
       ├─► If AVAILABLE: Atomically calls redeem_voucher() -> AccessEntitlement
       ├─► If REDEEMED: Verifies active authorizability
       │
       ▼ Returns credentials + target action URL
MikroTik Login Form Submission (POST http://10.5.50.1/login)
       │
       ▼ RADIUS Access-Request to FreeRADIUS / Django AAA
Internet Granted -> Customer Status Screen (Plan, Duration, Data Usage, Disconnect)
```

---

## 2. Key Architecture Principles

1. **Lightweight Customer Access Surface:** The captive portal is a focused, fast, standalone customer surface ($360\text{px}-430\text{px}$ mobile viewport) and does not load any admin dashboard dependencies or charts.
2. **Tenant & Voucher Isolation:** Vouchers are strictly scoped to the company resolved by the Hotspot slug. A voucher belonging to Company B cannot be validated or redeemed on Company A's portal.
3. **Decoupled Router Handoff:** The portal communicates with the central Django AAA engine over HTTPS/REST and submits standard credentials to MikroTik HotSpot over `$(link-login-only)` to grant physical layer access.
4. **Bilingual Support:** Built-in English (`EN`) and Kiswahili (`SW`) localization for instructions, status metrics, and customer-safe error messages.
