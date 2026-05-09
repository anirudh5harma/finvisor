from __future__ import annotations

from typing import Any

from ..core.config import Settings, get_settings
from ..data.loader import DataLoader
from ..llm.generator import AnswerGenerator
from ..schemas import ChatResponse
from ..services.evaluator import ResponseEvaluator
from ..services.intent_router import ChatIntent, IntentRouter
from ..services.market_intelligence import MarketIntelligence
from ..services.portfolio_analytics import PortfolioAnalytics
from ..services.reasoning_engine import ReasoningEngine


class ChatAgent:
    def __init__(self, loader: DataLoader, settings: Settings | None = None) -> None:
        self.loader = loader
        self.settings = settings or get_settings()
        self.market = MarketIntelligence(
            loader.market_data,
            loader.news_data,
            loader.historical_data,
            loader.sector_mapping,
        )
        self.analytics = PortfolioAnalytics(loader.mutual_funds_data, settings=self.settings)
        self.generator = AnswerGenerator(settings=self.settings)
        self.evaluator = ResponseEvaluator()
        self.intent_router = IntentRouter()

    def answer(self, message: str, portfolio_id: str | None = None) -> ChatResponse:
        intent = self.intent_router.route(message)
        query_context: dict[str, Any] = {}
        portfolio_analysis = None
        symbols: set[str] = set()
        sectors: set[str] = set()

        fund_code = self.loader.find_mutual_fund_code(message)
        stock_symbol = self.loader.find_stock_symbol(message)
        if fund_code:
            intent = ChatIntent.MUTUAL_FUND_ANALYSIS
        elif stock_symbol:
            intent = ChatIntent.STOCK_ANALYSIS
        elif intent in {ChatIntent.MUTUAL_FUND_ANALYSIS, ChatIntent.STOCK_ANALYSIS}:
            intent = ChatIntent.GENERAL_FINANCE

        if portfolio_id:
            portfolio = self.loader.get_portfolio(portfolio_id)
            portfolio_analysis = self.analytics.analyze(portfolio_id, portfolio)
            symbols = set(portfolio_analysis["symbols"])
            sectors = set(portfolio_analysis["sectors"])

        if intent == ChatIntent.MARKET_SUMMARY:
            symbols = set()
            sectors = set()

        market_summary = self.market.market_summary()
        sector_trends = self.market.sector_trends()
        if intent == ChatIntent.STOCK_ANALYSIS:
            stock = self.loader.get_stock(stock_symbol or "")
            stock_sector = stock.get("sector") if stock else None
            news_items = self.market.relevant_news(
                symbols={stock_symbol} if stock_symbol else set(),
                sectors={stock_sector} if stock_sector else set(),
                limit=self.settings.max_relevant_news,
            )
            query_context = {"question": message, "symbol": stock_symbol, "stock": stock, "news": news_items}
        elif intent == ChatIntent.MUTUAL_FUND_ANALYSIS:
            fund = self.loader.get_mutual_fund(fund_code or "")
            fund_sectors = set(fund.get("sector_allocation", {}).keys()) if fund else set()
            fund_symbols = {
                item.get("stock")
                for item in (fund or {}).get("top_holdings", []) + (fund or {}).get("top_equity_holdings", [])
                if isinstance(item, dict) and item.get("stock")
            }
            news_items = self.market.relevant_news(
                symbols=fund_symbols,
                sectors=fund_sectors,
                limit=self.settings.max_relevant_news,
            )
            query_context = {"question": message, "scheme_code": fund_code, "mutual_fund": fund, "news": news_items}
        elif intent == ChatIntent.MARKET_SUMMARY:
            news_items = self.market.market_drivers(limit=self.settings.max_relevant_news)
        else:
            news_items = self.market.relevant_news(
                symbols=symbols,
                sectors=sectors,
                limit=self.settings.max_relevant_news * 3,
            )
            query_context = {"question": message}
        reasoning_portfolio_analysis = (
            portfolio_analysis
            if intent
            in {
                ChatIntent.PORTFOLIO_IMPACT,
                ChatIntent.RISK_ANALYSIS,
                ChatIntent.CONFLICT_ANALYSIS,
                ChatIntent.TOP_MOVERS,
            }
            else None
        )
        reasoning = ReasoningEngine(
            self.loader.market_data,
            sector_trends,
            max_chains=max(self.settings.max_reasoning_chains * 3, self.settings.max_reasoning_chains),
            prefer_conflicts=intent == ChatIntent.CONFLICT_ANALYSIS,
        ).build_chains(
            reasoning_portfolio_analysis,
            news_items,
        )
        reasoning = self._select_reasoning(intent, reasoning)
        if intent in {ChatIntent.STOCK_ANALYSIS, ChatIntent.MUTUAL_FUND_ANALYSIS}:
            evidence = self._query_evidence(intent, query_context)
        else:
            evidence = self._evidence(reasoning, news_items)
        confidence = self._confidence(reasoning)
        generated = self.generator.generate(
            message,
            intent,
            portfolio_analysis,
            market_summary,
            reasoning,
            evidence,
            query_context=query_context,
        )
        evaluation = self.evaluator.evaluate(generated.text, bool(portfolio_analysis), reasoning, evidence, intent=intent)
        response_metadata = {
            "intent": intent.value,
            "provider": generated.provider,
            "model": generated.model,
            "prompt_version": generated.prompt_version,
            "token_usage": generated.token_usage,
            "fallback_reason": generated.fallback_reason,
        }

        return ChatResponse(
            answer=generated.text,
            confidence_score=confidence,
            reasoning_chains=reasoning,
            evidence=evidence,
            evaluation=evaluation,
            response_metadata=response_metadata,
        )

    def _evidence(self, reasoning: list[dict[str, Any]], news_items: list[dict[str, Any]]) -> dict[str, Any]:
        news_ids = sorted({chain.get("news_id") for chain in reasoning if chain.get("news_id")})
        symbols = sorted({chain.get("holding_id") for chain in reasoning if chain.get("holding_id")})
        sectors = sorted({chain.get("sector") for chain in reasoning if chain.get("sector")})
        return {
            "news_ids": news_ids,
            "symbols": symbols,
            "sectors": sectors,
            "news": [
                {
                    "id": item.get("id"),
                    "headline": item.get("headline"),
                    "sentiment": item.get("sentiment"),
                    "impact_level": item.get("impact_level"),
                    "relevance_score": item.get("relevance_score"),
                }
                for item in news_items
                if item.get("id") in news_ids
            ],
        }

    def _query_evidence(self, intent: ChatIntent, query_context: dict[str, Any]) -> dict[str, Any]:
        news_items = query_context.get("news", [])
        if intent == ChatIntent.STOCK_ANALYSIS:
            stock = query_context.get("stock") or {}
            symbols = [query_context["symbol"]] if query_context.get("symbol") else []
            sectors = [stock["sector"]] if stock.get("sector") else []
        else:
            fund = query_context.get("mutual_fund") or {}
            symbols = [
                item.get("stock")
                for item in fund.get("top_holdings", [])[:5]
                if isinstance(item, dict) and item.get("stock")
            ]
            sectors = list((fund.get("sector_allocation") or {}).keys())[:5]

        return {
            "news_ids": [item.get("id") for item in news_items[:5] if item.get("id")],
            "symbols": symbols,
            "sectors": sectors,
            "news": [
                {
                    "id": item.get("id"),
                    "headline": item.get("headline"),
                    "sentiment": item.get("sentiment"),
                    "impact_level": item.get("impact_level"),
                    "relevance_score": item.get("relevance_score"),
                }
                for item in news_items[:5]
            ],
        }

    def _confidence(self, reasoning: list[dict[str, Any]]) -> float:
        if not reasoning:
            return 0.35
        return round(sum(chain.get("confidence", 0.5) for chain in reasoning) / len(reasoning), 2)

    def _select_reasoning(self, intent: ChatIntent, reasoning: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if intent == ChatIntent.CONFLICT_ANALYSIS:
            conflicts = [chain for chain in reasoning if chain.get("conflict")]
            non_conflicts = [chain for chain in reasoning if not chain.get("conflict")]
            if conflicts:
                return conflicts[: self.settings.max_reasoning_chains]
            return non_conflicts[: self.settings.max_reasoning_chains]
        return reasoning[: self.settings.max_reasoning_chains]
