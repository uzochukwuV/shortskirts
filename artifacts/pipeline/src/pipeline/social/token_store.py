from __future__ import annotations

import base64
import hashlib
import os

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover - used only before dependencies are installed
    Fernet = None


def _key_bytes() -> bytes:
    raw = os.getenv("SOCIAL_TOKEN_ENCRYPTION_KEY") or os.getenv("SECRET_KEY") or "storyforge-local-dev-token-key"
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _fernet():
    if Fernet is None:
        return None
    key = base64.urlsafe_b64encode(_key_bytes())
    return Fernet(key)


def _xor_crypt(data: bytes) -> bytes:
    key = _key_bytes()
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


def encrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    fernet = _fernet()
    if fernet:
        return "fernet:" + fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    return "local:" + base64.urlsafe_b64encode(_xor_crypt(value.encode("utf-8"))).decode("utf-8")


def decrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("fernet:"):
        fernet = _fernet()
        if not fernet:
            raise RuntimeError("cryptography is required to decrypt this social token")
        return fernet.decrypt(value.removeprefix("fernet:").encode("utf-8")).decode("utf-8")
    if value.startswith("local:"):
        return _xor_crypt(base64.urlsafe_b64decode(value.removeprefix("local:").encode("utf-8"))).decode("utf-8")
    fernet = _fernet()
    if fernet:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    return _xor_crypt(base64.urlsafe_b64decode(value.encode("utf-8"))).decode("utf-8")
