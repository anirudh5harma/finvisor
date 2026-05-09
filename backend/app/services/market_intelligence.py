from __future__ import annotations

from typing import Any


IMPACT_WEIGHT = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}
SCOPE_WEIGHT = {"STOCK_SPECIFIC": 3.0, "SECTOR_SPECIFIC": 2.0, "MARKET_WIDE": 1.5}


class MarketIntelligence:
    def __init__(
        self,
        market_data: dict[str, Any],
        news_data: dict[str, Any],
        historical_data: dict[str, Any],
        sector_mapping: dict[str, Any],
    ) -> None:
        self.market_data = market_data
        self.news_data = news_data
        self.historical_data = historical_data
        self.sector_mapping = sector_mapping

    def market_summary(self) -> dict[str, Any]:
        indices = self.market_data.get("indices", {})
        breadth = self.historical_data.get("market_breadth", {})
        index_changes = [item.get("change_percent", 0.0) for item in indices.values()]
        avg_change = sum(index_changes) / len(index_changes) if index_changes else 0.0
        breadth_ratio = breadth.get("nifty50", {}).get("advance_decline_ratio", 1.0)

        if avg_change <= -0.5 or breadth_ratio < 0.7:
            sentiment = "BEARISH"
        elif avg_change >= 0.5 and breadth_ratio > 1.2:
            sentiment = "BULLISH"
        else:
            sentiment = "NEUTRAL"

        return {
            "date": self.market_data.get("metadata", {}).get("date"),
            "sentiment": sentiment,
            "average_index_change_percent": round(avg_change, 2),
            "indices": indices,
            "market_breadth": breadth,
            "fii_dii_data": self.historical_data.get("fii_dii_data", {}),
            "top_news": self.top_market_news(limit=5),
        }

    def sector_trends(self) -> dict[str, dict[str, Any]]:
        sectors = self.market_data.get("sector_performance", {})
        stocks = self.market_data.get("stocks", {})
        trends: dict[str, dict[str, Any]] = {}

        for sector, sector_data in sectors.items():
            sector_stocks = [
                stock
                for stock in stocks.values()
                if stock.get("sector") == sector and stock.get("change_percent") is not None
            ]
            derived_change = (
                sum(stock["change_percent"] for stock in sector_stocks) / len(sector_stocks)
                if sector_stocks
                else sector_data.get("change_percent", 0.0)
            )
            trends[sector] = {
                **sector_data,
                "derived_change_percent": round(derived_change, 2),
                "weekly": self.historical_data.get("sector_weekly_performance", {}).get(sector),
                "mapping": self.sector_mapping.get("sectors", {}).get(sector, {}),
            }
        return trends

    def top_market_news(self, limit: int = 5) -> list[dict[str, Any]]:
        return sorted(
            self.news_data.get("news", []),
            key=lambda item: (
                IMPACT_WEIGHT.get(item.get("impact_level"), 0.0),
                abs(item.get("sentiment_score", 0.0)),
            ),
            reverse=True,
        )[:limit]

    def classified_news(self) -> list[dict[str, Any]]:
        return [
            {
                "id": item.get("id"),
                "headline": item.get("headline"),
                "sentiment": item.get("sentiment"),
                "sentiment_score": item.get("sentiment_score"),
                "scope": item.get("scope"),
                "impact_level": item.get("impact_level"),
                "entities": item.get("entities", {}),
                "classification_source": "provided_dataset_tags",
            }
            for item in self.news_data.get("news", [])
        ]

    def market_drivers(self, limit: int = 8) -> list[dict[str, Any]]:
        ranked: list[tuple[float, dict[str, Any]]] = []
        for item in self.news_data.get("news", []):
            if item.get("scope") not in {"MARKET_WIDE", "SECTOR_SPECIFIC"}:
                continue
            score = (
                1 if item.get("scope") == "MARKET_WIDE" else 0,
                IMPACT_WEIGHT.get(item.get("impact_level"), 0.0),
                abs(item.get("sentiment_score", 0.0)),
            )
            relevance_score = score[0] * 5 + score[1] + score[2]
            ranked.append((relevance_score, {**item, "relevance_score": round(relevance_score, 2)}))
        return [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:limit]]

    def relevant_news(
        self,
        symbols: set[str] | None = None,
        sectors: set[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        symbols = symbols or set()
        sectors = sectors or set()
        ranked: list[tuple[float, dict[str, Any]]] = []

        for item in self.news_data.get("news", []):
            entities = item.get("entities", {})
            news_symbols = set(entities.get("stocks", []))
            news_sectors = set(entities.get("sectors", []))
            symbol_overlap = len(symbols & news_symbols)
            sector_overlap = len(sectors & news_sectors)
            market_wide = 1 if item.get("scope") == "MARKET_WIDE" else 0
            if not (symbol_overlap or sector_overlap or market_wide):
                continue

            score = (
                symbol_overlap * 6.0
                + sector_overlap * 3.0
                + market_wide
                + IMPACT_WEIGHT.get(item.get("impact_level"), 0.0)
                + SCOPE_WEIGHT.get(item.get("scope"), 0.0)
                + abs(item.get("sentiment_score", 0.0))
            )
            if score > 0:
                ranked.append((score, {**item, "relevance_score": round(score, 2)}))

        return [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:limit]]
