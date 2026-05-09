from __future__ import annotations

from typing import Any


POSITIVE = {"POSITIVE"}
NEGATIVE = {"NEGATIVE"}


class ReasoningEngine:
    def __init__(
        self,
        market_data: dict[str, Any],
        sector_trends: dict[str, dict[str, Any]],
        max_chains: int = 5,
        prefer_conflicts: bool = False,
    ) -> None:
        self.market_data = market_data
        self.sector_trends = sector_trends
        self.max_chains = max_chains
        self.prefer_conflicts = prefer_conflicts

    def build_chains(
        self,
        portfolio_analysis: dict[str, Any] | None,
        news_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not portfolio_analysis:
            return self._market_chains(news_items)

        holdings = portfolio_analysis.get("holding_impacts", [])
        chains: list[dict[str, Any]] = []
        for holding in holdings:
            matched_news = self._news_for_holding(holding, news_items)
            if not matched_news:
                continue

            primary_news = matched_news[0]
            sector = holding.get("sector")
            sector_data = self.sector_trends.get(sector, {})
            confidence = self._confidence(holding, primary_news, sector_data)
            chains.append(
                {
                    "news_id": primary_news.get("id"),
                    "headline": primary_news.get("headline"),
                    "news_sentiment": primary_news.get("sentiment"),
                    "impact_level": primary_news.get("impact_level"),
                    "sector": sector,
                    "sector_change_percent": sector_data.get("change_percent")
                    or sector_data.get("derived_change_percent"),
                    "holding_id": holding.get("id"),
                    "holding_name": holding.get("name"),
                    "holding_day_change_percent": holding.get("day_change_percent"),
                    "holding_day_change": holding.get("day_change"),
                    "portfolio_impact_percent": holding.get("portfolio_impact_percent"),
                    "causal_factors": primary_news.get("causal_factors", []),
                    "conflict": self._has_conflict(primary_news, holding),
                    "confidence": confidence,
                    "rank_score": round(
                        abs(holding.get("portfolio_impact_percent", 0.0)) * 10
                        + primary_news.get("relevance_score", 0.0)
                        + confidence,
                        3,
                    ),
                }
            )

        return sorted(chains, key=lambda item: item["rank_score"], reverse=True)[: self.max_chains]

    def _market_chains(self, news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chains = []
        for news in news_items[:5]:
            for sector in news.get("entities", {}).get("sectors", [])[:2]:
                sector_data = self.sector_trends.get(sector, {})
                chains.append(
                    {
                        "news_id": news.get("id"),
                        "headline": news.get("headline"),
                        "news_sentiment": news.get("sentiment"),
                        "impact_level": news.get("impact_level"),
                        "sector": sector,
                        "sector_change_percent": sector_data.get("change_percent")
                        or sector_data.get("derived_change_percent"),
                        "causal_factors": news.get("causal_factors", []),
                        "confidence": 0.75,
                        "rank_score": news.get("relevance_score", 0.0),
                    }
                )
        return sorted(chains, key=lambda item: item["rank_score"], reverse=True)[: self.max_chains]

    def _news_for_holding(self, holding: dict[str, Any], news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        holding_id = holding.get("id")
        sector = holding.get("sector")
        top_holdings = set(holding.get("top_holdings", []))
        matches = []
        for news in news_items:
            entities = news.get("entities", {})
            stocks = set(entities.get("stocks", []))
            sectors = set(entities.get("sectors", []))
            if holding_id in stocks or sector in sectors or top_holdings & stocks or news.get("scope") == "MARKET_WIDE":
                matches.append(news)

        def portfolio_explanation_score(item: dict[str, Any]) -> float:
            entities = item.get("entities", {})
            score = item.get("relevance_score", 0.0)
            if item.get("scope") == "MARKET_WIDE" and sector in entities.get("sectors", []):
                score += 8.0
            if holding_id in entities.get("stocks", []):
                score += 3.0
            if self.prefer_conflicts and self._has_conflict(item, holding):
                score += 12.0
            elif self._sentiment_aligns_with_price(item, holding):
                score += 5.0
            elif self._has_conflict(item, holding):
                score -= 4.0
            return score

        return sorted(matches, key=portfolio_explanation_score, reverse=True)

    def _sentiment_aligns_with_price(self, news: dict[str, Any], holding: dict[str, Any]) -> bool:
        sentiment = news.get("sentiment")
        movement = holding.get("day_change_percent", 0.0)
        return (sentiment in NEGATIVE and movement < 0) or (sentiment in POSITIVE and movement > 0)

    def _has_conflict(self, news: dict[str, Any], holding: dict[str, Any]) -> bool:
        entities = news.get("entities", {})
        direct_stocks = set(entities.get("stocks", []))
        top_holdings = set(holding.get("top_holdings", []))
        if holding.get("id") not in direct_stocks and not (top_holdings & direct_stocks):
            return False

        sentiment = news.get("sentiment")
        movement = holding.get("day_change_percent", 0.0)
        return (sentiment in POSITIVE and movement < 0) or (sentiment in NEGATIVE and movement > 0)

    def _confidence(
        self,
        holding: dict[str, Any],
        news: dict[str, Any],
        sector_data: dict[str, Any],
    ) -> float:
        score = 0.45
        entities = news.get("entities", {})
        if holding.get("id") in entities.get("stocks", []):
            score += 0.25
        if holding.get("sector") in entities.get("sectors", []):
            score += 0.15
        if news.get("impact_level") == "HIGH":
            score += 0.1
        sector_change = sector_data.get("change_percent") or sector_data.get("derived_change_percent") or 0.0
        holding_change = holding.get("day_change_percent", 0.0)
        if sector_change and holding_change and sector_change * holding_change > 0:
            score += 0.05
        return round(min(score, 0.95), 2)
