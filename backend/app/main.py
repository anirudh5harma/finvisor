from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .dependencies import get_chat_agent, get_loader
from .services.market_intelligence import MarketIntelligence
from .services.portfolio_analytics import PortfolioAnalytics
from .schemas import ChatRequest, ChatResponse
from .observability import flush_observability, observability_status, trace


settings = get_settings()


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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/observability/status")
def get_observability_status() -> dict:
    return observability_status()


@app.get("/api/portfolios")
def list_portfolios() -> list[dict]:
    return get_loader().list_portfolios()


@app.get("/api/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str) -> dict:
    loader = get_loader()
    try:
        portfolio = loader.get_portfolio(portfolio_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PortfolioAnalytics(loader.mutual_funds_data).analyze(portfolio_id, portfolio)


@app.get("/api/market/summary")
def market_summary() -> dict:
    loader = get_loader()
    return MarketIntelligence(
        loader.market_data,
        loader.news_data,
        loader.historical_data,
        loader.sector_mapping,
    ).market_summary()


@app.get("/api/news/classified")
def classified_news() -> list[dict]:
    loader = get_loader()
    return MarketIntelligence(
        loader.market_data,
        loader.news_data,
        loader.historical_data,
        loader.sector_mapping,
    ).classified_news()


@app.get("/api/stocks/{symbol}")
def get_stock(symbol: str) -> dict:
    loader = get_loader()
    stock = loader.get_stock(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    market = MarketIntelligence(loader.market_data, loader.news_data, loader.historical_data, loader.sector_mapping)
    news = market.relevant_news(symbols={symbol.upper()}, sectors={stock.get("sector")}, limit=5)
    return {"symbol": symbol.upper(), "stock": stock, "news": news}


@app.get("/api/mutual-funds/{scheme_code}")
def get_mutual_fund(scheme_code: str) -> dict:
    loader = get_loader()
    fund = loader.get_mutual_fund(scheme_code)
    if not fund:
        raise HTTPException(status_code=404, detail=f"Unknown scheme_code: {scheme_code}")
    return {"scheme_code": scheme_code.upper(), "mutual_fund": fund}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    with trace("chat_request", {"portfolio_id": request.portfolio_id, "message": request.message}) as span:
        try:
            response = get_chat_agent().answer(request.message, request.portfolio_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        span.update(
            confidence_score=response.confidence_score,
            evaluation_score=response.evaluation.score,
            evidence=response.evidence,
            answer=response.answer,
            response_metadata=response.response_metadata,
            reasoning_chain_count=len(response.reasoning_chains),
        )
        return response
