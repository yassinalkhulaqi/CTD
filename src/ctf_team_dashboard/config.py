"""Application configuration for the CTF Team Dashboard.

Settings are resolved from environment variables with a ``CTFD_`` prefix so the
same image can be promoted between environments without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_TRUE_VALUES = frozenset({"1", "true", "yes", "on", "y"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off", "n"})


def _env(name: str, default: str | None = None) -> str | None:
    """Return an environment variable value, or ``default`` when unset."""
    raw = os.environ.get(f"CTFD_{name}")
    if raw is None:
        return default
    stripped = raw.strip()
    return stripped if stripped else default


def _env_bool(name: str, default: bool) -> bool:
    """Return a boolean environment flag."""
    raw = _env(name)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise ValueError(f"CTFD_{name} must be a boolean value, got {raw!r}")


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    """Return an integer environment value with a lower bound."""
    raw = _env(name)
    if raw is None:
        return default
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"CTFD_{name} must be an integer, got {raw!r}") from exc
    if parsed < minimum:
        raise ValueError(f"CTFD_{name} must be >= {minimum}, got {parsed}")
    return parsed


def _env_float(name: str, default: float, *, minimum: float = 0.0) -> float:
    """Return a float environment value with a lower bound."""
    raw = _env(name)
    if raw is None:
        return default
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise ValueError(f"CTFD_{name} must be a number, got {raw!r}") from exc
    if parsed < minimum:
        raise ValueError(f"CTFD_{name} must be >= {minimum}, got {parsed}")
    return parsed


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration for the CTF Team Dashboard."""

    database_path: Path = Path("ctf_team_dashboard.sqlite")
    api_prefix: str = "/api"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    seed_on_startup: bool = True
    log_level: str = "INFO"
    request_timeout_seconds: float = 30.0
    auth_secret: str = "change-me-in-production"
    access_token_ttl_seconds: int = 3600
    rate_limit_per_minute: int = 240
    allowed_origins: tuple[str, ...] = field(default=("http://localhost:5173",))
    auth_enabled: bool = False
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 14
    static_dir: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the process environment."""
        origins_raw = _env("CORS_ORIGINS") or "http://localhost:5173"
        origins = tuple(origin.strip() for origin in origins_raw.split(",") if origin.strip())
        return cls(
            database_path=Path(_env("DATABASE_PATH", "ctf_team_dashboard.sqlite") or ""),
            api_prefix=_env("API_PREFIX", "/api") or "/api",
            cors_origins=origins,
            allowed_origins=origins,
            seed_on_startup=_env_bool("SEED_ON_STARTUP", True),
            log_level=(_env("LOG_LEVEL", "INFO") or "INFO").upper(),
            request_timeout_seconds=_env_float("REQUEST_TIMEOUT_SECONDS", 30.0),
            auth_secret=_env("AUTH_SECRET", "change-me-in-production") or "",
            access_token_ttl_seconds=_env_int("ACCESS_TOKEN_TTL_SECONDS", 3600, minimum=60),
            rate_limit_per_minute=_env_int("RATE_LIMIT_PER_MINUTE", 240, minimum=1),
            auth_enabled=_env_bool("AUTH_ENABLED", False),
            refresh_token_ttl_seconds=_env_int(
                "REFRESH_TOKEN_TTL_SECONDS", 60 * 60 * 24 * 14, minimum=300
            ),
            static_dir=_env("STATIC_DIR"),
        )

    @property
    def is_production(self) -> bool:
        """Return whether the dashboard runs with production safeguards."""
        return self.log_level in {"WARNING", "ERROR", "CRITICAL"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings.from_env()


def reset_settings_cache() -> None:
    """Clear the settings cache so tests can re-resolve the environment."""
    get_settings.cache_clear()
