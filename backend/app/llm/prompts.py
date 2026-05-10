from __future__ import annotations

from typing import Any

from ..services.intent_router import ChatIntent


SYSTEM_PROMPT = (
    "Answer Indian market portfolio questions using causal reasoning. "
    "Link macro/news events to sector moves to stock or mutual fund impact. "
    "Use only the provided evidence and computed analytics. Do not fabricate live prices, "
    "do not give direct buy/sell instructions. Keep responses compact."
)

GENERAL_FINANCE_SYSTEM_PROMPT = (
    "Answer general finance education questions directly and concisely. "
    "Do not add market commentary, portfolio analysis, news drivers, or current-data claims "
    "unless the user explicitly asks for them. Do not give direct buy/sell instructions."
)


def build_answer_prompt(
    question: str,
    intent: ChatIntent,
    portfolio_analysis: dict[str, Any] | None,
    market_summary: dict[str, Any],
    reasoning_chains: list[dict[str, Any]],
    query_context: dict[str, Any],
) -> str:
    compact_portfolio = None
    if portfolio_analysis:
        compact_portfolio = {
            "portfolio_id": portfolio_analysis.get("portfolio_id"),
            "risk_profile": portfolio_analysis.get("risk_profile"),
            "day_change_percent": portfolio_analysis.get("day_change_percent"),
            "day_change_absolute": portfolio_analysis.get("day_change_absolute"),
            "sector_allocation": portfolio_analysis.get("sector_allocation"),
            "asset_type_allocation": portfolio_analysis.get("asset_type_allocation"),
            "risk_metrics": portfolio_analysis.get("risk_metrics"),
            "top_detractors": portfolio_analysis.get("top_detractors", [])[:3],
            "top_gainers": portfolio_analysis.get("top_gainers", [])[:3],
        }

    compact_market = None
    if intent != ChatIntent.GENERAL_FINANCE:
        compact_market = {
            "sentiment": market_summary.get("sentiment"),
            "average_index_change_percent": market_summary.get("average_index_change_percent"),
            "market_breadth": market_summary.get("market_breadth", {}).get("nifty50"),
            "fii_dii_data": market_summary.get("fii_dii_data"),
        }
    compact_query_context = {
        key: value
        for key, value in query_context.items()
        if key in {"symbol", "stock", "scheme_code", "mutual_fund"}
    }

    base_prompt = (
        f"Question: {question}\n"
        f"Intent: {intent.value}\n"
        f"Portfolio summary: {compact_portfolio}\n"
        f"Market summary: {compact_market}\n"
        f"Query context: {compact_query_context}\n"
        f"Top reasoning chains: {reasoning_chains[:5]}\n"
    )
    if intent == ChatIntent.GENERAL_FINANCE:
        return (
            base_prompt
            + "Answer as a concise educational finance explanation. Do not add market commentary, current drivers, "
            "portfolio impact, or news unless the question explicitly asks for them. End with 'Not financial advice.'"
        )
    return (
        base_prompt
        + "Answer using only this evidence in at most 4 short bullets and 120 words. "
        "Prioritize only the highest-impact causal links, include key numbers, mention ambiguity only if present, "
        "avoid buy/sell instructions, and end with 'Not financial advice.'"
    )
