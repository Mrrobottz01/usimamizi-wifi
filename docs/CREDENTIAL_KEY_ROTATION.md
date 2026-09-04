# Credential & Key Rotation Specification

Technical specification for managing and rotating Fernet authenticated encryption keys (`CREDENTIAL_ENCRYPTION_KEY`) in **Usimamizi Wi-Fi** (Phase 5).

---

## 1. Key Configuration & Environment Isolation

- **Production Policy:** In production environments, `CREDENTIAL_ENCRYPTION_KEY` must be configured explicitly in environment variables / secret vault. Deriving from Django `SECRET_KEY` is forbidden in production.
- **Development Policy:** In local lab / test environments, fallback to `settings.SECRET_KEY` is permitted for automated development setups.

---

## 2. Key Rotation Procedure

When `CREDENTIAL_ENCRYPTION_KEY` needs to be rotated:

1. **Step 1: Set Old Key in Environment**
   Configure `CREDENTIAL_ENCRYPTION_KEY_OLD` alongside `CREDENTIAL_ENCRYPTION_KEY` (the new key).

2. **Step 2: Run Secret Re-encryption Management Task**
   Decrypt existing rows with `OLD_KEY` and re-encrypt with `NEW_KEY` atomically:
   ```python
   from apps.radius.models import RadiusClient
   for client in RadiusClient.objects.all():
       raw = client.shared_secret
       client.shared_secret = raw
       client.save(update_fields=['shared_secret_encrypted'])
   ```

3. **Step 3: Decommission Old Key**
   Remove `CREDENTIAL_ENCRYPTION_KEY_OLD` from the environment.
