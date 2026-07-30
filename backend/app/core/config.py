"""Application settings loaded from environment variables.

The module intentionally provides usable development defaults.  In particular,
external API keys are optional so importing the application never fails merely
because an AI or public-data integration has not been configured yet.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Final

DEFAULT_DATABASE_URL: Final[str] = "sqlite:///./joopjoop.db"
DEFAULT_SECRET_KEY: Final[str] = "change-this-secret-in-production"


def _read_bool(name: str, default: bool) -> bool:
    """Read a conventional boolean environment variable."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int) -> int:
    """Read an integer environment variable with a clear error message."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _read_cors_origins() -> tuple[str, ...]:
    """Read CORS origins from either a JSON array or a comma-separated value."""

    raw_value = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).strip()
    if not raw_value:
        return ()

    if raw_value.startswith("["):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise ValueError("CORS_ORIGINS must be valid JSON or comma-separated") from exc
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError("CORS_ORIGINS JSON value must be an array of strings")
        return tuple(item.strip() for item in parsed if item.strip())

    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration.

    MySQL is selected in deployment by setting ``DATABASE_URL``.  SQLite is the
    default to keep local development and isolated tests import-safe.
    """

    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "joopjoop API"))
    api_v1_prefix: str = field(default_factory=lambda: os.getenv("API_V1_PREFIX", "/api/v1"))
    debug: bool = field(default_factory=lambda: _read_bool("DEBUG", False))
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default_factory=lambda: _read_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    )
    auto_create_tables: bool = field(
        default_factory=lambda: _read_bool("AUTO_CREATE_TABLES", False)
    )
    cors_origins: tuple[str, ...] = field(default_factory=_read_cors_origins)
    upstage_api_key: str | None = field(
        default_factory=lambda: os.getenv("UPSTAGE_API_KEY") or os.getenv("SOLAR_API_KEY") or None
    )
    solar_model: str = field(default_factory=lambda: os.getenv("SOLAR_MODEL", "solar-pro2"))
    youth_policy_api_key: str | None = field(
        default_factory=lambda: os.getenv("YOUTH_POLICY_API_KEY") or None
    )
    smtp_host: str | None = field(default_factory=lambda: os.getenv("SMTP_HOST") or None)
    smtp_port: int = field(default_factory=lambda: _read_int("SMTP_PORT", 587))
    smtp_username: str | None = field(default_factory=lambda: os.getenv("SMTP_USERNAME") or None)
    smtp_password: str | None = field(default_factory=lambda: os.getenv("SMTP_PASSWORD") or None)
    smtp_from_email: str | None = field(
        default_factory=lambda: os.getenv("SMTP_FROM_EMAIL") or None
    )
    smtp_use_tls: bool = field(default_factory=lambda: _read_bool("SMTP_USE_TLS", True))

    def __post_init__(self) -> None:
        """Validate settings that must always have meaningful values."""

        if not self.database_url.strip():
            raise ValueError("DATABASE_URL cannot be empty")
        if not self.secret_key:
            raise ValueError("SECRET_KEY cannot be empty")
        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable settings object."""

    return Settings()


settings = get_settings()


__all__ = ["Settings", "get_settings", "settings"]
