# RADIUS Shared Secret Security & Encryption Specification

Comprehensive technical specification of RADIUS shared secret storage, encryption at rest, key management, and API protection rules in **Usimamizi Wi-Fi** (Phase 4B).

---

## 1. Requirement & Architectural Rationale

To provision NAS clients, generate FreeRADIUS `clients.conf` definitions, and support automated router rotation, Usimamizi Wi-Fi requires **reversible authenticated encryption** of RADIUS shared secrets.

Plain hashing (e.g. SHA-256 or bcrypt) or unencrypted base64 serialization does not fulfill this requirement because FreeRADIUS requires the original shared secret string to compute the MD5 authenticator hash over RADIUS UDP packets (RFC 2865).

---

## 2. Cryptographic Storage Mechanism

- **Algorithm:** Authenticated Symmetric Encryption using **Fernet** (AES-128-CBC with PKCS7 padding and HMAC-SHA256 for integrity verification).
- **Ciphertext Format:** URL-safe Base64-encoded token conforming to the Fernet specification (`gAAAAA...`).
- **Key Derivation:** Derived dynamically from `settings.CREDENTIAL_ENCRYPTION_KEY` (or fallback to `settings.SECRET_KEY`) using SHA-256 digest encoding into 32 URL-safe bytes.

```text
Plaintext Secret ("radius_shared_secret_lab")
        │
        ▼ (Fernet Encryption / AES-128-CBC + HMAC-SHA256)
Encrypted Ciphertext at Rest ("gAAAAABqmHvcxnKJKcIZ...") in `radius_clients.shared_secret_encrypted`
        │
        ▼ (Fernet Decryption via .shared_secret property)
Plaintext Secret (only in-memory when FreeRADIUS client config is rendered)
```

---

## 3. Key Management & Environment Isolation

| Environment | Encryption Key Source | Storage Policy |
| :--- | :--- | :--- |
| **Development / Lab** | `CREDENTIAL_ENCRYPTION_KEY` in `.env` | Local development secret |
| **Production / Staging** | Secure Environment Variable / Vault | Rotated independently from Django `SECRET_KEY` |

---

## 4. API & Audit Exposure Rules

1. **Write-Only in REST Serializers:** `shared_secret` is declared with `write_only=True` in `RadiusClientSerializer`.
2. **Never Returned in API Responses:** `GET /api/v1/radius/clients/` never outputs raw or encrypted secrets.
3. **Never Logged:** Logging filters and debug serializers redact shared secrets.
4. **Audit Payload Redaction:** Audit log change tracking redacts `shared_secret` from `changes` payloads.
