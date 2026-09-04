# API Conventions & Architecture Guide

**System Name:** Usimamizi Wi-Fi  
**Base Namespace:** `/api/v1/`  

---

## 1. Authentication & Headers

All authenticated API requests require a JSON Web Token (JWT) in the HTTP Authorization header:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## 2. Standardized Error Response Format

All error responses across all backend domains follow a single unified schema:

```json
{
  "code": "VALIDATION_ERROR",
  "detail": "The request contains invalid data.",
  "field_errors": {
    "email": ["This field is required."]
  }
}
```

### Standard Error Codes
- `VALIDATION_ERROR` (400 Bad Request)
- `UNAUTHENTICATED` (401 Unauthorized)
- `AUTHENTICATION_FAILED` (401 Unauthorized)
- `PERMISSION_DENIED` (403 Forbidden)
- `NOT_FOUND` (404 Not Found)
- `INTERNAL_SERVER_ERROR` (500 Internal Server Error)

---

## 3. Core Phase 0 Endpoints

### System Health
- `GET /api/v1/health/` (Unauthenticated) — Returns DB and Redis connectivity status.

### Accounts & Auth
- `POST /api/v1/accounts/auth/login/` (Unauthenticated) — Accepts `email` & `password`, returns `access`, `refresh` tokens and user payload.
- `POST /api/v1/accounts/auth/logout/` (Authenticated) — Client discards session token.
- `GET /api/v1/accounts/auth/me/` (Authenticated) — Retrieves current authenticated user profile.

### Multi-Tenant Companies
- `GET /api/v1/companies/` (Authenticated) — Lists companies that the authenticated user belongs to.
- `GET /api/v1/companies/{id}/` (Authenticated) — Retrieves company detail. Enforces tenant boundaries (returns 403 Forbidden on cross-tenant requests).
