from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

from .config import get_settings


settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("financial_advisor")
_trace_write_lock = threading.Lock()
_last_trace_id: str | None = None
_last_flush_error: str | None = None
_last_flush_at: float | None = None


@lru_cache(maxsize=1)
def _get_langfuse_client() -> Any | None:
    settings = get_settings()
    if not settings.langfuse_enabled or not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    try:
        from langfuse import Langfuse

        kwargs = {
            "public_key": settings.langfuse_public_key,
            "secret_key": settings.langfuse_secret_key,
            "timeout": settings.langfuse_timeout_seconds,
        }
        if settings.langfuse_base_url:
            kwargs["base_url"] = settings.langfuse_base_url
        return Langfuse(**kwargs)
    except Exception:
        logger.exception("Failed to initialize Langfuse client")
        return None


class TraceContext:
    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        self.name = name
        self.metadata = metadata or {}
        self.start = time.perf_counter()
        self.observation = None
        self.trace_id = None
        self._latest_metadata = self.metadata

        client = _get_langfuse_client()
        if client:
            with _trace_write_lock:
                try:
                    if hasattr(client, "start_observation"):
                        self.observation = client.start_observation(
                            name=name,
                            as_type="generation",
                            input=self.metadata.get("message"),
                            metadata=self.metadata,
                        )
                        self.trace_id = getattr(self.observation, "trace_id", None)
                        if self.trace_id:
                            _record_trace_id(self.trace_id)
                except Exception:
                    logger.exception("Failed to create Langfuse observation")

    def update(self, **kwargs: Any) -> None:
        payload = {**self.metadata, **kwargs}
        if self.observation:
            with _trace_write_lock:
                try:
                    self._update_observation(payload)
                except Exception:
                    logger.exception("Failed to update Langfuse observation")
        log_payload = {
            key: value for key, value in payload.items() if key not in {"answer", "message", "response_metadata"}
        }
        if self.trace_id:
            log_payload["langfuse_trace_id"] = self.trace_id
        logger.info(json.dumps({"event": self.name, **log_payload}, default=str))

    def close(self) -> None:
        latency_ms = round((time.perf_counter() - self.start) * 1000, 2)
        if self.observation:
            with _trace_write_lock:
                try:
                    self.observation.update(metadata={**self._latest_metadata, "latency_ms": latency_ms})
                    self.observation.end()
                    self.observation = None
                except Exception:
                    logger.exception("Failed to close Langfuse observation")
        if get_settings().langfuse_flush_on_request:
            flush_observability()
        self.update(latency_ms=latency_ms)

    def _update_observation(self, payload: dict[str, Any]) -> None:
        metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"answer", "message", "response_metadata"}
        }
        self._latest_metadata = metadata
        response_metadata = payload.get("response_metadata") or {}
        self.observation.update(
            output=payload.get("answer"),
            model=response_metadata.get("model"),
            usage_details=_langfuse_usage(response_metadata.get("token_usage") or {}),
            metadata=metadata,
        )


@contextmanager
def trace(name: str, metadata: dict[str, Any] | None = None) -> Iterator[TraceContext]:
    context = TraceContext(name, metadata)
    try:
        yield context
    finally:
        context.close()


def flush_observability() -> None:
    global _last_flush_at, _last_flush_error
    client = _get_langfuse_client()
    if not client:
        return

    with _trace_write_lock:
        try:
            client.flush()
            _last_flush_at = time.time()
            _last_flush_error = None
        except Exception:
            _last_flush_error = "flush_failed"
            logger.exception("Failed to flush Langfuse client")


def _record_trace_id(trace_id: str) -> None:
    global _last_trace_id
    _last_trace_id = trace_id


def _langfuse_usage(token_usage: dict[str, int]) -> dict[str, int] | None:
    if not token_usage:
        return None
    return {
        "input": int(token_usage.get("prompt_tokens", 0)),
        "output": int(token_usage.get("completion_tokens", 0)),
        "total": int(token_usage.get("total_tokens", 0)),
    }


def observability_status() -> dict[str, Any]:
    settings = get_settings()
    client = _get_langfuse_client()
    auth_valid = None
    if client:
        try:
            auth_valid = client.auth_check()
        except Exception:
            logger.exception("Langfuse auth check failed")
            auth_valid = False
    return {
        "langfuse_enabled": settings.langfuse_enabled,
        "langfuse_configured": bool(settings.langfuse_public_key and settings.langfuse_secret_key),
        "langfuse_base_url_configured": bool(settings.langfuse_base_url),
        "langfuse_flush_on_request": settings.langfuse_flush_on_request,
        "client_initialized": client is not None,
        "auth_valid": auth_valid,
        "last_trace_id": _last_trace_id,
        "last_trace_url": client.get_trace_url(trace_id=_last_trace_id) if client and _last_trace_id else None,
        "last_flush_at": _last_flush_at,
        "last_flush_error": _last_flush_error,
    }
