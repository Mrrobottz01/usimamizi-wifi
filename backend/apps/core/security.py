import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _get_encryption_key() -> bytes:
    """
    Derive a 32-byte URL-safe base64-encoded key for Fernet authenticated encryption.
    Sources key from settings.CREDENTIAL_ENCRYPTION_KEY or falls back to settings.SECRET_KEY.
    """
    key_source = getattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', None) or settings.SECRET_KEY
    digest = hashlib.sha256(key_source.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plain_text: Optional[str]) -> str:
    """
    Encrypt sensitive secrets (e.g. RADIUS shared secrets, API credentials) at rest
    using Fernet authenticated encryption (AES-128-CBC with HMAC-SHA256).
    """
    if not plain_text:
        return ""
    fernet = Fernet(_get_encryption_key())
    return fernet.encrypt(plain_text.encode('utf-8')).decode('utf-8')


def decrypt_secret(cipher_text: Optional[str]) -> str:
    """
    Decrypt Fernet-encrypted ciphertext into original plaintext.
    Handles legacy plaintext or signed values gracefully during migration.
    """
    if not cipher_text:
        return ""
    try:
        fernet = Fernet(_get_encryption_key())
        return fernet.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except (InvalidToken, ValueError, Exception):
        # Fallback: check if it's a legacy Django-signed string (e.g. InJhZGl1c19zaGFyZWRfc2VjcmV0X2xhYiI:...)
        if ":" in cipher_text:
            parts = cipher_text.split(":")
            if len(parts) == 3:
                try:
                    import base64
                    import json
                    decoded = base64.urlsafe_b64decode(parts[0] + "==").decode('utf-8')
                    return json.loads(decoded) if decoded.startswith('"') else decoded
                except Exception:
                    pass
        return cipher_text
