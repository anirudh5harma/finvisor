from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api.router import api_router
from .core.config import get_settings
from .core.logging import configure_logging, log_event
from .telemetry.langfuse import flush_observability


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("financial_advisor.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    flush_observability()


app = FastAPI(title="Autonomous Financial Advisor Chat Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.middleware("http")
async def structured_request_logging(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log_event(
            logger,
            "http_request_failed",
            level=logging.ERROR,
            exc_info=True,
            method=request.method,
            path=request.url.path,
            query=bool(request.url.query),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        raise

    log_event(
        logger,
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round((time.perf_counter() - start) * 1000, 2),
    )
    return response

