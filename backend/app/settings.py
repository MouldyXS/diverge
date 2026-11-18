"""Application settings from environment variables. Standard library only.

Each limit has one owner: `DIVERGE_MAX_WORDS` is passed to `AnalysisService`, which keeps its own default and its own
range check (so its default value is not repeated here); `DIVERGE_MAX_BODY_BYTES` belongs to the HTTP layer only. Host,
port and shutdown timing are Uvicorn command-line options, not settings.

Error messages name the variable but never repeat its value.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_MAX_BODY_BYTES = 262144  # 256 KiB
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")  # the Vite development server
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class SettingsError(ValueError):
    """A setting is missing its expected form. The message names the variable, not its value."""


def _digits(name: str, value: str) -> int:
    if not (value.isascii() and value.isdigit()):
        raise SettingsError(f"{name} must be a non-negative integer written with ASCII digits")
    return int(value)


def _origin(name: str, value: str) -> str:
    error = SettingsError(f"{name} must hold origins of the form http(s)://host[:port], separated by commas")
    if not value or "*" in value or any(ch.isspace() for ch in value):
        raise error
    try:
        parts = urlsplit(value)
        port = parts.port  # raises ValueError for an invalid port
    except ValueError:
        raise error from None
    if (parts.scheme not in ("http", "https") or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.path or parts.query or parts.fragment or "?" in value
            or "#" in value or (port is not None and not 0 < port < 65536)):
        raise error
    return value


@dataclass(frozen=True)
class AppSettings:
    max_words: int | None = None  # None: AnalysisService applies its own default
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS  # empty: CORS disabled
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if self.max_words is not None and (isinstance(self.max_words, bool) or not isinstance(self.max_words, int)):
            raise SettingsError("max_words must be an integer or None")
        if isinstance(self.max_body_bytes, bool) or not isinstance(self.max_body_bytes, int) or self.max_body_bytes <= 0:
            raise SettingsError("max_body_bytes must be a positive integer")
        if not isinstance(self.cors_origins, tuple):
            raise SettingsError("cors_origins must be a tuple of origins")
        for origin in self.cors_origins:
            _origin("cors_origins", origin if isinstance(origin, str) else "")
        if self.log_level not in LOG_LEVELS:
            raise SettingsError(f"log_level must be one of {', '.join(LOG_LEVELS)}")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AppSettings:
        """Read the DIVERGE_* variables. A missing variable keeps its default; an invalid one raises SettingsError."""
        env = os.environ if environ is None else environ
        values: dict[str, object] = {}
        if "DIVERGE_MAX_WORDS" in env:
            values["max_words"] = _digits("DIVERGE_MAX_WORDS", env["DIVERGE_MAX_WORDS"])
        if "DIVERGE_MAX_BODY_BYTES" in env:
            size = _digits("DIVERGE_MAX_BODY_BYTES", env["DIVERGE_MAX_BODY_BYTES"])
            if size <= 0:
                raise SettingsError("DIVERGE_MAX_BODY_BYTES must be a positive integer")
            values["max_body_bytes"] = size
        if "DIVERGE_CORS_ORIGINS" in env:
            raw = env["DIVERGE_CORS_ORIGINS"].strip()
            values["cors_origins"] = (() if not raw else
                                      tuple(_origin("DIVERGE_CORS_ORIGINS", item.strip()) for item in raw.split(",")))
        if "DIVERGE_LOG_LEVEL" in env:
            level = env["DIVERGE_LOG_LEVEL"].strip().upper()
            if level not in LOG_LEVELS:
                raise SettingsError(f"DIVERGE_LOG_LEVEL must be one of {', '.join(LOG_LEVELS)}")
            values["log_level"] = level
        return cls(**values)
