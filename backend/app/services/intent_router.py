from __future__ import annotations

from enum import StrEnum


class ChatIntent(StrEnum):
    PORTFOLIO_IMPACT = "portfolio_impact"
    RISK_ANALYSIS = "risk_analysis"
    CONFLICT_ANALYSIS = "conflict_analysis"
    MARKET_SUMMARY = "market_summary"
    TOP_MOVERS = "top_movers"
    STOCK_ANALYSIS = "stock_analysis"
    MUTUAL_FUND_ANALYSIS = "mutual_fund_analysis"
    GENERAL_FINANCE = "general_finance"


class IntentRouter:
    def route(self, message: str) -> ChatIntent:
        normalized = message.lower()
        educational_query = normalized.startswith(
            (
                "what is",
                "what are",
                "define",
                "explain",
                "how does",
                "how do",
                "meaning of",
                "difference between",
                "compare",
            )
        )
        current_data_query = any(
            term in normalized
            for term in (
                "today",
                "current",
                "latest",
                "live",
                "now",
                "news",
                "sentiment",
                "nifty",
                "sensex",
                "indices",
                "index",
                "portfolio",
                "holding",
                "my portfolio",
                "my holding",
            )
        )

        if educational_query and not current_data_query:
            return ChatIntent.GENERAL_FINANCE

        if any(term in normalized for term in ("mutual fund", "fund", "scheme", "nav", "expense ratio")):
            return ChatIntent.MUTUAL_FUND_ANALYSIS
        if any(term in normalized for term in ("stock", "share", "symbol", "price", "volume", "pe ratio", "p/e")):
            return ChatIntent.STOCK_ANALYSIS
        if any(term in normalized for term in ("conflict", "diverg", "positive news", "negative price", "mixed signal")):
            return ChatIntent.CONFLICT_ANALYSIS
        if any(term in normalized for term in ("risk", "concentration", "exposure", "volatile", "beta")):
            return ChatIntent.RISK_ANALYSIS
        if any(term in normalized for term in ("market", "sentiment", "nifty", "sensex", "indices")):
            return ChatIntent.MARKET_SUMMARY
        if any(term in normalized for term in ("gainer", "loser", "mover", "best", "worst")):
            return ChatIntent.TOP_MOVERS
        if not any(term in normalized for term in ("portfolio", "holding", "fall", "down", "up", "lost", "gain", "moved", "today")):
            return ChatIntent.GENERAL_FINANCE
        return ChatIntent.PORTFOLIO_IMPACT
