from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dependencies import get_loader
from ...services.portfolio_analytics import PortfolioAnalytics


router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("")
def list_portfolios() -> list[dict]:
    return get_loader().list_portfolios()


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: str) -> dict:
    loader = get_loader()
    try:
        portfolio = loader.get_portfolio(portfolio_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PortfolioAnalytics(loader.mutual_funds_data).analyze(portfolio_id, portfolio)
