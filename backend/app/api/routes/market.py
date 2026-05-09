from __future__ import annotations

from fastapi import APIRouter

from ..dependencies import get_loader
from ...services.market_intelligence import MarketIntelligence


router = APIRouter(tags=["market"])


@router.get("/market/summary")
def market_summary() -> dict:
    loader = get_loader()
    return _market_service().market_summary()


@router.get("/news/classified")
def classified_news() -> list[dict]:
    return _market_service().classified_news()


def _market_service() -> MarketIntelligence:
    loader = get_loader()
    return MarketIntelligence(
        loader.market_data,
        loader.news_data,
        loader.historical_data,
        loader.sector_mapping,
    )
