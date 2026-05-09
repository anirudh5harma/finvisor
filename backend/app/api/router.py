from __future__ import annotations

from fastapi import APIRouter

from .routes import chat, health, instruments, market, observability, portfolios


api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(observability.router)
api_router.include_router(portfolios.router)
api_router.include_router(market.router)
api_router.include_router(instruments.router)
api_router.include_router(chat.router)
