from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dependencies import get_loader
from ...services.market_intelligence import MarketIntelligence


router = APIRouter(tags=["instruments"])


@router.get("/stocks/{symbol}")
def get_stock(symbol: str) -> dict:
    loader = get_loader()
    stock = loader.get_stock(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    market = MarketIntelligence(loader.market_data, loader.news_data, loader.historical_data, loader.sector_mapping)
    news = market.relevant_news(symbols={symbol.upper()}, sectors={stock.get("sector")}, limit=5)
    return {"symbol": symbol.upper(), "stock": stock, "news": news}


@router.get("/mutual-funds/{scheme_code}")
def get_mutual_fund(scheme_code: str) -> dict:
    loader = get_loader()
    fund = loader.get_mutual_fund(scheme_code)
    if not fund:
        raise HTTPException(status_code=404, detail=f"Unknown scheme_code: {scheme_code}")
    return {"scheme_code": scheme_code.upper(), "mutual_fund": fund}
