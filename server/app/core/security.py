from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from server.app.core.config import get_settings


# ── JWT Operations ────────────────────────────────────────────────

def create_access_token(subject: str, scopes: list[str] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.security.jwt_access_token_expire_minutes),
        "jti": secrets.token_hex(16),
        "scope": scopes or [],
        "type": "access",
    }
    return jwt.encode(payload, settings.security.jwt_secret, algorithm="HS256")


def create_refresh_token(subject: str) -> tuple[str, str]:
    """Returns (token_string, jti) — jti is stored in Redis for revocation."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    jti = secrets.token_hex(16)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=settings.security.jwt_refresh_token_expire_days),
        "jti": jti,
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.security.jwt_secret, algorithm="HS256")
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])


# ── Component Auth ────────────────────────────────────────────────

def create_component_token(component_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": component_id,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "jti": secrets.token_hex(16),
        "type": "component",
    }
    return jwt.encode(payload, settings.security.jwt_secret, algorithm="HS256")


def generate_hmac(message: bytes, secret: bytes) -> str:
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_hmac(message: bytes, secret: bytes, signature: str) -> bool:
    expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Encryption ────────────────────────────────────────────────────

def generate_encryption_key() -> bytes:
    """Generate a 256-bit AES key."""
    return AESGCM.generate_key(bit_length=256)


def encrypt_data(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """Encrypt data using AES-256-GCM. Returns (ciphertext, iv)."""
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, plaintext, None)
    return ciphertext, iv


def decrypt_data(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt data using AES-256-GCM."""
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ciphertext, None)


# ── Key Derivation ────────────────────────────────────────────────

def generate_shared_secret() -> str:
    """Generate a shared secret for component HMAC authentication."""
    return secrets.token_hex(32)
