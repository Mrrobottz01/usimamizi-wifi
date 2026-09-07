# Infrastructure Refactor — Phase F: Captive Portal Router-Aware Handoff

## 1. Executive Summary

Phase F resolves the legacy flat/singleton assumptions regarding captive portal login redirection in Usimamizi Wi-Fi. 
Previously, login handoff relied on static, hardcoded defaults (`http://10.5.50.1/login`, static `router_login_url`, and company default fallbacks). 
Phase F replaces this with a strictly **hotspot-aware and router-aware handoff pipeline**:

```text
portal slug (/p/:slug)
       ↓
exact HotspotConfiguration
       ↓
exact Router & Gateway IP
       ↓
validated runtime link-login / derived gateway handoff
       ↓
tamper-resistant signed portal context token
       ↓
safe RouterOS login submission (HTTP PAP)
       ↓
safe post-auth destination redirect (link-orig / safe fallback)
```

Phase F ensures that multi-hotspot and multi-router architectures operate with strict isolation, eliminates open redirect vulnerabilities, and guarantees payment and voucher idempotency during captive network handoff retries.

---

## 2. Captive Portal Handoff Precedence (Section 4, 25)

The handoff login URL is resolved dynamically via `get_hotspot_login_url(hotspot, runtime_context=None)` using a deterministic 3-tier fallback chain:

1. **Tier 1 (Validated Runtime MikroTik Parameter):**
   If MikroTik passes `link-login` or `link-login-only` (e.g. `http://10.5.50.1/login`) in the initial HTTP 302 captive redirect, this URL is validated against the hotspot's verified network context. If valid, it is treated as authoritative for that customer session.
2. **Tier 2 (Configured HotSpot Override):**
   If no runtime parameter is passed, and `hotspot.router_login_url` has an explicit custom override (e.g., custom FQDN `https://hotspot.operator.tz/login`), that override is returned.
3. **Tier 3 (Derived Gateway URL):**
   If `hotspot.gateway_ip` is configured (e.g. `10.5.60.1`), the system derives `http://<gateway_ip>/login`. If `router_login_url` still contains the legacy default (`http://10.5.50.1/login`) but the hotspot gateway is `10.5.60.1`, Tier 3 supersedes the default to prevent cross-hotspot misrouting.
4. **Safety Net:**
   If all resolution options are absent, the system falls back to `http://10.5.50.1/login`.

---

## 3. Security Validation & Open-Redirect Protection (Section 6, 20)

### 3.1 Handoff URL Validation (`validate_handoff_login_url`)
Runtime handoff targets are strictly validated before acceptance:
- **Allowed Schemes:** `http://` or `https://` only (rejects `javascript:`, `file:`, `data:`).
- **Host Restrictions:**
  - Must match `hotspot.gateway_ip`
  - OR match `hotspot.router.management_ip`
  - OR match the hostname of the configured `router_login_url`
  - OR be an RFC1918 private IPv4 address within the hotspot gateway's `/24` subnet.
- **Explicit Denials:**
  - Cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`)
  - Loopback (`localhost`, `127.0.0.1`)
  - Untrusted external public hostnames and phishing domains.

### 3.2 Destination Redirect Sanitization (`validate_destination_url`)
The client's original browsing destination (`link-orig`, `dst`) is sanitized:
- Must begin with `http://` or `https://`.
- Dangerous schemes (`javascript:`, `file:`) safely fallback to `https://www.google.com`.
- Self-referential portal URLs (e.g. `.../p/:slug`) are rejected to prevent captive portal redirect loops (`portal -> login -> portal -> login`).

---

## 4. Tamper-Resistant Signed Portal Context (Section 7, 8, 9, 31)

### 4.1 Token Architecture
To preserve state across mobile application switching (e.g., leaving the browser to enter an M-Pesa PIN in a mobile money app) and page refreshes, the backend issues a signed, time-limited cryptographic token via Django's `TimestampSigner(salt='usimamizi-portal-context-v1')`.

```json
{
  "hotspot_id": "5274adf6-0b9e-480a-8be5-8e15c0c4aa7e",
  "hotspot_slug": "usimamizi-lab",
  "router_id": "91f664e9-51c5-4eb2-a451-9045e7b2714c",
  "location_id": "a1b2c3d4-...",
  "gateway_ip": "10.5.50.1",
  "link_login": "http://10.5.50.1/login",
  "link_orig": "https://www.google.com",
  "mac": "56:E9:1A:C4:15:3E",
  "ip": "10.5.50.250",
  "issued_at": "2026-09-05T16:28:49.123456+00:00"
}
```

### 4.2 Security Guarantees
- **Expiry:** Default maximum validity of 3,600 seconds (1 hour). Expired tokens are rejected.
- **Tenant & Hotspot Bound:** The decoded `hotspot_id` must match the target `HotspotConfiguration`. A token issued for Hotspot A cannot be reused on Hotspot B.
- **Tampering Detection:** Any modification to the base64 or signature invalidates the token immediately (`BadSignature`).
- **No Secret Exposure:** Only public-safe parameters are serialized; RouterOS API credentials and RADIUS secrets are never included.

---

## 5. API Endpoints

### 5.1 Portal Context Initialization
`POST /api/v1/public/hotspots/{slug}/portal-context/`
- **Request Parameters:**
  - `link_login`: Runtime MikroTik `link-login` query param
  - `link_orig` / `dst`: Customer target website
  - `mac`: Client MAC address (from MikroTik redirect query param)
  - `ip`: Client IP address (from MikroTik redirect query param)
- **Response:**
  - `hotspot`: Public branding metadata
  - `login_url`: Validated target RouterOS login endpoint
  - `gateway_ip`: Hotspot gateway IP
  - `context_token`: Signed cryptographic context token
  - `session_context`: Non-sensitive session context parameters
  - `plans`: Active Wi-Fi packages available on this hotspot

### 5.2 Public HotSpot Portal Config
`GET /api/v1/public/hotspots/{slug}/portal/`
- Enhanced to return validated `login_url`, `gateway_ip`, and initial `context_token`.

### 5.3 Voucher Redemption
`POST /api/v1/public/hotspots/{slug}/voucher/`
- Accepts `context_token` and `link_login`.
- Emits structured telemetry: `PORTAL_HANDOFF_ATTEMPTED`.
- Returns `router_login_url` and `gateway_ip`.

### 5.4 Self-Service Purchase & Polling
`POST /api/v1/public/hotspots/{slug}/purchases/`
- Persists exact `hotspot` foreign key on the `AccessPurchase` entity.
`GET /api/v1/public/purchases/{reference}/status/`
- Returns dynamic `router_login_url` and `gateway_ip` resolved from `purchase.hotspot`.

---

## 6. Frontend Captive Portal UX & Recovery States (Section 41, 42, 43, 44)

The captive portal frontend (`frontend/src/features/portal/CaptivePortalPage.tsx`) implements 5 distinct states:

1. **Selection & Purchase:** Packages or voucher code entry.
2. **Payment In-Flight:** Real-time polling with USSD mobile money instructions and hosted checkout links.
3. **Activation State (`ACTIVATING`):**
   - Displays: *"Activating your Wi-Fi... Connecting your device to the hotspot gateway"* / *"Inawasha Wi-Fi yako... Inaunganisha kifaa chako kwenye kisanduku"*.
   - Automatically submits credentials to the validated `actionUrl` via a hidden iframe.
4. **Handoff Failure & Safe Retry (`FAILED`):**
   - Displays: *"Access Ready, Pending Router Handoff"* / *"Kifurushi Kiko Tayari, Kinangoja Kisanduku"*.
   - Explains that payment/redemption succeeded, but the local Wi-Fi router did not complete the connection.
   - **[Retry Connection]**: Resubmits credentials to the validated router endpoint without generating a new charge or consuming another voucher.
   - **[Go to My Account]**: Allows access to account status.
5. **Connected State (`CONNECTED`):**
   - Displays active voucher code, plan name, remaining time, and remaining data allowance.
   - Dynamic router links based on `hotspot.gateway_ip` (e.g. `http://<gateway_ip>/status` and `http://<gateway_ip>/logout`).
   - "Start Browsing" opens the sanitized `destinationUrl`.
   - "Trouble connecting?" link allows manual transition to `FAILED` for retry.

---

## 7. Multi-Hotspot & Same-Router Isolation (Section 22, 23)

- Hotspots hosted on different VLANs/interfaces of the same router (e.g., Guest on `10.5.50.1` and VIP on `10.5.60.1`):
  - Guest portal authenticates strictly to `http://10.5.50.1/login`.
  - VIP portal authenticates strictly to `http://10.5.60.1/login`.
  - Tokens and handoffs cannot cross subnets or hotspots.
- If a hotspot is moved to a new router, new portal sessions automatically target the new router and gateway while preserving historical purchases and session logs.

---

## 8. Test Verification & Results

### 8.1 Backend Test Suite (`test_phase_f_portal_handoff.py`)
- `test_get_hotspot_login_url_precedence`: Verifies 3-tier precedence.
- `test_validate_handoff_login_url_security`: Verifies rejection of SSRF, javascript, file, and external domains.
- `test_validate_destination_url_security`: Verifies open-redirect protection and loop prevention.
- `test_signed_portal_context_lifecycle`: Verifies signing, verification, tampering detection, and expiry.
- `test_public_portal_context_endpoint`: Verifies HTTP 200 contract of `/portal-context/`.
- `test_disabled_hotspot_rejection`: Verifies HTTP 403 on disabled hotspots.
- `test_voucher_redemption_retains_hotspot_and_safe_retry`: Verifies idempotent retry without burning vouchers.
- `test_purchase_status_returns_hotspot_router_login_url`: Verifies purchase polling returns hotspot gateway login URL.

**Full backend regression suite:**
- **178 of 178 tests passed** (0 failures) in 28.24s.

### 8.2 Frontend Test Suite (`CaptivePortalPage.test.tsx`)
- Validates 3-tier precedence logic.
- Validates dynamic gateway status and logout URL derivation.
- Validates post-auth destination sanitization.
- Validates slug-scoped sessionStorage key names.

**Full frontend suite:**
- **17 of 17 tests passed** (0 failures) in 2.65s.
- `npm run build`: Zero errors, production bundle compiled in 10.68s.

---

## 9. Physical Lab Verification

| Component | Target / Value | Result |
| :--- | :--- | :--- |
| **Physical Router** | MikroTik hAP ac lite (`192.168.1.107:8728`) | **PASSED** (Online, connected in 61ms) |
| **Physical Gateway** | `10.5.50.1` (`Usimamizi Lab HotSpot`) | **PASSED** (Resolves to `http://10.5.50.1/login`) |
| **Active Client Device** | Phone (`56:E9:1A:C4:15:3E` at `10.5.50.250`) | **PASSED** (Active hotspot session `MZ76-E8Y4`, 68 MB downloaded) |
| **Public API Probe** | `POST /portal-context/` & `GET /portal/` | **PASSED** (Status 200, returned signed token & valid login URL) |

---

## 10. Acceptance Matrix

| Requirement | Status | Notes |
| :--- | :---: | :--- |
| Hotspot-specific portal resolution | **PASSED** | Resolves exact hotspot configuration from slug |
| Runtime link-login capture & validation | **PASSED** | Validates incoming MikroTik `link-login` |
| Handoff validation against gateway/subnet | **PASSED** | Rejects malicious external and cloud metadata URLs |
| Signed portal context token | **PASSED** | TimestampSigner with tamper-resistance and 1h expiry |
| Multi-hotspot isolation | **PASSED** | Verified in `test_signed_portal_context_lifecycle` |
| Same-router hotspot isolation | **PASSED** | Different gateways on same router resolve distinct URLs |
| Dynamic gateway handoff | **PASSED** | Derived from `hotspot.gateway_ip` |
| Purchase hotspot persistence | **PASSED** | `AccessPurchase.hotspot` populated and returned |
| Voucher hotspot persistence | **PASSED** | Voucher redemption returns hotspot-bound login URL |
| Safe retry without duplicate charge/voucher | **PASSED** | Entitlement preserved; retry resubmits existing credentials |
| Open redirect protection | **PASSED** | Sanitizes destination URLs; prevents loop |
| Disabled hotspot handling | **PASSED** | Returns HTTP 403 `HOTSPOT_INACTIVE` |
| Walled garden context alignment | **PASSED** | Entries synchronized by exact hotspot/company |
| Frontend activation state | **PASSED** | Dedicated activating spinner with progress |
| Frontend failure & retry state | **PASSED** | Friendly retry card without duplicate payment |
| Multilingual support (EN / SW) | **PASSED** | Full Swahili & English localization for all new states |
| Full backend regression | **PASSED** | 178 / 178 tests passed |
| Full frontend test suite | **PASSED** | 17 / 17 tests passed |
| Frontend production build | **PASSED** | Clean Vite build in 10.68s |
| Physical lab handoff connectivity | **PASSED** | Physical hAP ac lite online, active session running |
| Secondary physical VLAN test | **NOT TESTED** | Single physical radio lab (synthetic tests passed) |

---

## 11. Phase G Prerequisites

Phase F is fully complete. The infrastructure is now ready for **Phase G: FreeRADIUS Multi-NAS Provisioning**:
1. All captive portal handoffs are router-aware and hotspot-aware.
2. The exact router and NAS IP are deterministically bound to each hotspot.
3. Client sessions authenticate against the correct NAS client configuration in FreeRADIUS.
