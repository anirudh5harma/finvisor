from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]


def load_environment() -> None:
    """Load local env files once without overriding shell-provided values."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    load_dotenv(ROOT_DIR / ".env.local", override=False)
    load_dotenv(ROOT_DIR / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    data_dir: Path = ROOT_DIR
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    log_level: str = "INFO"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_enabled: bool | None = None
    openai_timeout_seconds: int = 30
    openai_max_retries: int = 1
    openai_max_output_tokens: int = 220
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str | None = None
    langfuse_enabled: bool = True
    langfuse_timeout_seconds: int = 5
    langfuse_flush_on_request: bool = True
    max_relevant_news: int = 10
    max_reasoning_chains: int = 5
    concentration_threshold_percent: float = 40.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_environment()
    data_dir = Path(os.getenv("DATA_DIR", Settings.data_dir))
    cors_origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", ",".join(Settings.cors_origins)).split(",")
        if origin.strip()
    )
    return Settings(
        data_dir=data_dir,
        cors_origins=cors_origins,
        log_level=os.getenv("LOG_LEVEL", Settings.log_level),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", Settings.openai_model),
        openai_enabled=_optional_env_bool("OPENAI_ENABLED"),
        openai_timeout_seconds=int(os.getenv("OPENAI_TIMEOUT", Settings.openai_timeout_seconds)),
        openai_max_retries=int(os.getenv("OPENAI_MAX_RETRIES", Settings.openai_max_retries)),
        openai_max_output_tokens=int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", Settings.openai_max_output_tokens)),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY") or None,
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY") or None,
        langfuse_base_url=os.getenv("LANGFUSE_BASE_URL") or None,
        langfuse_enabled=_env_bool("LANGFUSE_ENABLED", Settings.langfuse_enabled),
        langfuse_timeout_seconds=int(os.getenv("LANGFUSE_TIMEOUT", Settings.langfuse_timeout_seconds)),
        langfuse_flush_on_request=_env_bool("LANGFUSE_FLUSH_ON_REQUEST", Settings.langfuse_flush_on_request),
        max_relevant_news=int(os.getenv("MAX_RELEVANT_NEWS", Settings.max_relevant_news)),
        max_reasoning_chains=int(os.getenv("MAX_REASONING_CHAINS", Settings.max_reasoning_chains)),
        concentration_threshold_percent=float(
            os.getenv("CONCENTRATION_THRESHOLD_PERCENT", Settings.concentration_threshold_percent)
        ),
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _optional_env_bool(name: str) -> bool | None:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}
