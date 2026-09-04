# RADIUS API Security & Machine-to-Machine Integration

Documentation of security controls protecting FreeRADIUS to Django REST API communications.

---

## 1. Machine-to-Machine Authentication

- FreeRADIUS `rlm_rest` communicates directly with Django on `/api/v1/radius/authorize/` and `/api/v1/radius/accounting/`.
- Authentication is enforced via `X-RADIUS-API-KEY` or `Authorization: Bearer <token>` matching `settings.RADIUS_API_SECRET`.
- When configured, unauthenticated requests are rejected immediately with `HTTP 403 Forbidden`.

---

## 2. Shared Secret Encryption at Rest

- All RADIUS client shared secrets (`RadiusClient.shared_secret_encrypted`) are cryptographically encrypted at rest using HMAC-SHA256 salted signing and base64 serialization.
- Shared secrets are marked `write_only` in serializers, never returned over REST APIs, never logged in log files, and never exposed in error responses.

---

## 3. Two Trust Boundaries

```text
Boundary 1: FreeRADIUS  ────────(X-RADIUS-API-KEY)───────►  Django API
Boundary 2: MikroTik NAS  ──────(RADIUS Shared Secret)───►  FreeRADIUS Server
```
- Authenticating the REST API request does not bypass NAS authorization.
- The Django authorization service still validates that `nas_ip` or `nas_identifier` corresponds to an active `RadiusClient` registered to the appropriate tenant.
