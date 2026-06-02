"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ENV_FILE = ".env"
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


@dataclass(frozen=True)
class AppSettings:
    """Runtime settings shared across application layers."""

    llm_api_key: str | None
    llm_model: str | None
    llm_base_url: str
    llm_timeout_seconds: float
    llm_max_retries: int
    dataset_cache_dir: str
    max_candidates: int
    top_k_output: int
    log_level: str

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key and self.llm_model and self.llm_base_url)


def load_settings(env: Mapping[str, str] | None = None) -> AppSettings:
    """Load settings from an environment mapping.

    `env` exists to keep tests deterministic. Production callers should use
    the process environment by leaving it unset.
    """

    source = _load_env_file(DEFAULT_ENV_FILE) if env is None else env

    max_candidates = _read_positive_int(source, "MAX_CANDIDATES", default=30)
    top_k_output = _read_positive_int(source, "TOP_K_OUTPUT", default=5)

    if top_k_output > max_candidates:
        raise ConfigError("TOP_K_OUTPUT must be less than or equal to MAX_CANDIDATES")

    return AppSettings(
        llm_api_key=_clean_optional(source.get("LLM_API_KEY")),
        llm_model=_clean_optional(source.get("LLM_MODEL")),
        llm_base_url=source.get("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()
        or "https://api.groq.com/openai/v1",
        llm_timeout_seconds=_read_positive_float(source, "LLM_TIMEOUT_SECONDS", default=20.0),
        llm_max_retries=_read_non_negative_int(source, "LLM_MAX_RETRIES", default=1),
        dataset_cache_dir=source.get("DATASET_CACHE_DIR", ".cache/zomato").strip()
        or ".cache/zomato",
        max_candidates=max_candidates,
        top_k_output=top_k_output,
        log_level=_read_log_level(source),
    )


def require_llm_settings(settings: AppSettings) -> None:
    """Raise a clear error when a feature requires LLM configuration."""

    if not settings.llm_enabled:
        raise ConfigError(
            "LLM_API_KEY, LLM_MODEL, and LLM_BASE_URL are required for LLM-backed ranking"
        )


def _load_env_file(path: str) -> Mapping[str, str]:
    """Load simple KEY=VALUE pairs from a local .env file without overriding env vars."""

    merged = dict(os.environ)
    env_path = Path(path)
    if not env_path.exists():
        return merged

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in merged:
            merged[key] = value.strip().strip('"').strip("'")

    return merged


def _read_positive_int(source: Mapping[str, str], name: str, default: int) -> int:
    raw_value = source.get(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc

    if value <= 0:
        raise ConfigError(f"{name} must be greater than zero")

    return value


def _read_non_negative_int(source: Mapping[str, str], name: str, default: int) -> int:
    raw_value = source.get(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc

    if value < 0:
        raise ConfigError(f"{name} must be greater than or equal to zero")

    return value


def _read_positive_float(source: Mapping[str, str], name: str, default: float) -> float:
    raw_value = source.get(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc

    if value <= 0:
        raise ConfigError(f"{name} must be greater than zero")

    return value


def _read_log_level(source: Mapping[str, str]) -> str:
    value = source.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    if value not in VALID_LOG_LEVELS:
        raise ConfigError(f"LOG_LEVEL must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}")
    return value


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
