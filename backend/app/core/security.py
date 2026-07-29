"""Password hashing and JWT helpers.

Password verification is deliberately independent from the database layer.
PBKDF2-HMAC-SHA256 is available in Python's standard library, avoids native
package build issues, and stores all parameters needed for future verification.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import jwt

from app.core.config import settings

PASSWORD_SCHEME: Final[str] = "pbkdf2_sha256"
PBKDF2_ITERATIONS: Final[int] = 600_000
SALT_BYTES: Final[int] = 16


def _b64encode(value: bytes) -> str:
    """Encode bytes without padding for compact password hashes."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    """Decode a URL-safe base64 value whose padding was removed."""

    padded_value = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded_value.encode("ascii"))


def hash_password(password: str) -> str:
    """Hash a password using a fresh random salt."""

    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")

    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "$".join(
        (
            PASSWORD_SCHEME,
            str(PBKDF2_ITERATIONS),
            _b64encode(salt),
            _b64encode(digest),
        )
    )


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Safely verify a plaintext password against a stored encoded hash."""

    if not isinstance(plain_password, str) or not isinstance(password_hash, str):
        return False

    try:
        scheme, raw_iterations, raw_salt, raw_digest = password_hash.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        iterations = int(raw_iterations)
        if iterations <= 0:
            return False
        salt = _b64decode(raw_salt)
        expected_digest = _b64decode(raw_digest)
    except (ValueError, TypeError, binascii.Error):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(
    data: Mapping[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed access token from caller-supplied claims."""

    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    claims = dict(data)
    claims.update(
        {
            "iat": now,
            "exp": expires_at,
            "type": "access",
        }
    )
    return jwt.encode(
        claims,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed access token.

    ``jwt.InvalidTokenError`` (including expiry) is intentionally allowed to
    propagate so the API layer can translate it into the appropriate HTTP 401
    response without this module depending on FastAPI.
    """

    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("unexpected token type")
    return dict(payload)


get_password_hash = hash_password


__all__ = [
    "create_access_token",
    "decode_access_token",
    "get_password_hash",
    "hash_password",
    "verify_password",
]
