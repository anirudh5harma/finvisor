from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from ..core.config import Settings, get_settings
from ..core.logging import log_event
from ..services.intent_router import ChatIntent
from .openai_provider import OpenAIAnswerProvider
from .prompts import GENERAL_FINANCE_SYSTEM_PROMPT, SYSTEM_PROMPT, build_answer_prompt, build_general_finance_prompt


logger = logging.getLogger("financial_advisor.llm")


@dataclass(frozen=True)
class GeneratedAnswer:
    text: str
    provider: str
    model: str
    token_usage: dict[str, int] = field(default_factory=dict)
    prompt_version: str = "financial-advisor-v2"
    fallback_reason: str | None = None


class AnswerGenerator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate(
        self,
        question: str,
        intent: ChatIntent,
        portfolio_analysis: dict[str, Any] | None,
        market_summary: dict[str, Any],
        reasoning_chains: list[dict[str, Any]],
        evidence: dict[str, Any],
        query_context: dict[str, Any] | None = None,
    ) -> GeneratedAnswer:
        if intent == ChatIntent.GENERAL_FINANCE:
            should_use_openai = self.settings.openai_enabled is not False and bool(self.settings.openai_api_key)
            if should_use_openai:
                llm_answer = self._try_general_finance_openai(question)
                if llm_answer:
                    return llm_answer
            text = self._template_answer(
                question,
                intent,
                portfolio_analysis,
                market_summary,
                reasoning_chains,
                evidence,
                query_context or {},
            )
            return GeneratedAnswer(
                text=text,
                provider="deterministic",
                model="rule-template",
                token_usage=self._estimate_token_usage(question, text),
                fallback_reason="openai_key_missing_or_general_finance_call_failed",
            )

        should_use_openai = self.settings.openai_enabled is not False and bool(self.settings.openai_api_key)
        if should_use_openai:
            llm_answer = self._try_openai(
                question,
                intent,
                portfolio_analysis,
                market_summary,
                reasoning_chains,
                query_context or {},
            )
            if llm_answer:
                return llm_answer
            fallback_reason = "openai_call_failed"
        else:
            fallback_reason = "openai_key_missing_or_disabled"
        text = self._template_answer(
            question,
            intent,
            portfolio_analysis,
            market_summary,
            reasoning_chains,
            evidence,
            query_context or {},
        )
        return GeneratedAnswer(
            text=text,
            provider="deterministic",
            model="rule-template",
            token_usage=self._estimate_token_usage(question, text),
            fallback_reason=fallback_reason,
        )

    def _try_openai(
        self,
        question: str,
        intent: ChatIntent,
        portfolio_analysis: dict[str, Any] | None,
        market_summary: dict[str, Any],
        reasoning_chains: list[dict[str, Any]],
        query_context: dict[str, Any],
    ) -> GeneratedAnswer | None:
        try:
            prompt = build_answer_prompt(
                question,
                intent,
                portfolio_analysis,
                market_summary,
                reasoning_chains,
                query_context,
            )
            system_prompt = GENERAL_FINANCE_SYSTEM_PROMPT if intent == ChatIntent.GENERAL_FINANCE else SYSTEM_PROMPT
            provider_answer = OpenAIAnswerProvider(self.settings).generate(
                prompt,
                system_prompt=system_prompt,
            )
            answer_text = self._ensure_disclaimer(provider_answer.text)
            return GeneratedAnswer(
                text=answer_text,
                provider="openai",
                model=self.settings.openai_model,
                token_usage=provider_answer.token_usage,
            )
        except Exception as exc:
            log_event(
                logger,
                "openai_generation_failed",
                level=logging.WARNING,
                error_type=type(exc).__name__,
                fallback_provider="deterministic",
            )
            return None

    def _try_general_finance_openai(self, question: str) -> GeneratedAnswer | None:
        try:
            prompt = build_general_finance_prompt(question)
            provider_answer = OpenAIAnswerProvider(self.settings).generate(
                prompt,
                system_prompt=GENERAL_FINANCE_SYSTEM_PROMPT,
            )
            answer_text = self._ensure_disclaimer(provider_answer.text)
            return GeneratedAnswer(
                text=answer_text,
                provider="openai",
                model=self.settings.openai_model,
                token_usage=provider_answer.token_usage,
            )
        except Exception as exc:
            log_event(
                logger,
                "openai_general_finance_generation_failed",
                level=logging.WARNING,
                error_type=type(exc).__name__,
                fallback_provider="deterministic",
            )
            return None

    def _ensure_disclaimer(self, answer: str) -> str:
        if "not financial advice" in answer.lower():
            return answer
        return f"{answer.rstrip()}\n\nNot financial advice."

    def _template_answer(
        self,
        question: str,
        intent: ChatIntent,
        portfolio_analysis: dict[str, Any] | None,
        market_summary: dict[str, Any],
        reasoning_chains: list[dict[str, Any]],
        evidence: dict[str, Any],
        query_context: dict[str, Any],
    ) -> str:
        if intent == ChatIntent.STOCK_ANALYSIS:
            return self._stock_answer(query_context)
        if intent == ChatIntent.MUTUAL_FUND_ANALYSIS:
            return self._fund_answer(query_context)
        if intent == ChatIntent.GENERAL_FINANCE:
            return self._general_finance_answer(question)
        if intent == ChatIntent.MARKET_SUMMARY:
            return self._market_answer(market_summary, reasoning_chains)
        if intent == ChatIntent.RISK_ANALYSIS and portfolio_analysis:
            return self._risk_answer(portfolio_analysis)
        if intent == ChatIntent.CONFLICT_ANALYSIS:
            return self._conflict_answer(reasoning_chains)
        if intent == ChatIntent.TOP_MOVERS and portfolio_analysis:
            return self._movers_answer(portfolio_analysis)

        del evidence
        lines: list[str] = []

        if portfolio_analysis:
            lines.append(
                f"Your portfolio moved {portfolio_analysis['day_change_percent']}% today "
                f"({portfolio_analysis['day_change_absolute']:+,.0f} INR)."
            )
        else:
            lines.append(
                f"The market tone is {market_summary['sentiment'].lower()}, with the main indices averaging "
                f"{market_summary['average_index_change_percent']}%."
            )

        if reasoning_chains:
            lines.append("The main causal drivers are:")
            for chain in reasoning_chains[:3]:
                if chain.get("holding_id"):
                    conflict = " This is a conflict signal because news sentiment and price action diverged." if chain.get("conflict") else ""
                    lines.append(
                        f"- {chain['headline']} affected {chain.get('sector')} "
                        f"({chain.get('sector_change_percent')}%), which linked to {chain.get('holding_id')} "
                        f"moving {chain.get('holding_day_change_percent')}% and contributing "
                        f"{chain.get('portfolio_impact_percent')}% to the portfolio.{conflict}"
                    )
                else:
                    lines.append(
                        f"- {chain['headline']} affected {chain.get('sector')} "
                        f"({chain.get('sector_change_percent')}%)."
                    )

        if portfolio_analysis and portfolio_analysis.get("risk_metrics", {}).get("concentration_risk"):
            risk = portfolio_analysis["risk_metrics"]
            lines.append(
                f"Risk alert: {risk.get('largest_sector')} is {risk.get('largest_sector_weight')}% of the portfolio, "
                "above the 40% concentration threshold."
            )

        lines.append("This is an informational analysis based on the supplied data, not financial advice.")
        return "\n".join(lines)

    def _stock_answer(self, query_context: dict[str, Any]) -> str:
        stock = query_context.get("stock")
        news_items = query_context.get("news", [])
        if not stock:
            return (
                "I could not identify a stock symbol from the question. Ask with a symbol such as HDFCBANK, INFY, or TCS.\n"
                "This is an informational analysis based on the supplied data, not financial advice."
            )

        lines = [
            f"{query_context.get('symbol')} ({stock.get('name')}) is in {stock.get('sector')} and moved "
            f"{stock.get('change_percent')}% today to {stock.get('current_price')} INR.",
            f"Context: beta {stock.get('beta')}, P/E {stock.get('pe_ratio')}, volume {stock.get('volume'):,}.",
        ]
        if news_items:
            lines.append("Relevant news:")
            for item in news_items[:3]:
                lines.append(f"- {item.get('headline')} ({item.get('sentiment')}, {item.get('impact_level')})")
        lines.append("This is an informational analysis based on the supplied data, not financial advice.")
        return "\n".join(lines)

    def _fund_answer(self, query_context: dict[str, Any]) -> str:
        fund = query_context.get("mutual_fund")
        if not fund:
            return (
                "I could not identify a mutual fund scheme from the question. Ask with a scheme code such as MF001 or MF005.\n"
                "This is an informational analysis based on the supplied data, not financial advice."
            )

        returns = fund.get("returns", {})
        sectors = fund.get("sector_allocation", {})
        lines = [
            f"{fund.get('scheme_code')} ({fund.get('scheme_name')}) has NAV {fund.get('current_nav')} INR "
            f"and moved {fund.get('nav_change_percent')}% today.",
            f"Risk rating is {fund.get('risk_rating')} with expense ratio {fund.get('expense_ratio')}%.",
        ]
        if returns:
            lines.append(
                f"Returns: 1Y {returns.get('1_year')}%, 3Y CAGR {returns.get('3_year_cagr')}%, "
                f"5Y CAGR {returns.get('5_year_cagr')}%."
            )
        if sectors:
            lines.append("Largest sector exposures:")
            for sector, weight in sorted(sectors.items(), key=lambda item: item[1], reverse=True)[:4]:
                lines.append(f"- {sector}: {weight}%")
        lines.append("This is an informational analysis based on the supplied data, not financial advice.")
        return "\n".join(lines)

    def _general_finance_answer(
        self,
        question: str,
    ) -> str:
        normalized = question.lower()
        if "finance" in normalized:
            lines = [
                "Finance is the management of money, including how people, companies, and governments earn, save, invest, borrow, budget, and manage risk.",
                "Common areas include personal finance, corporate finance, investing, banking, insurance, taxation, and financial markets.",
            ]
        elif "mutual fund" in normalized:
            lines = [
                "A mutual fund pools money from investors and invests it across securities such as stocks, bonds, or arbitrage positions.",
                "For this project, mutual fund answers use NAV movement, risk rating, returns, expense ratio, top holdings, and sector allocation from the supplied data.",
            ]
        elif "beta" in normalized:
            lines = [
                "Beta measures how sensitive a stock or portfolio is to market movement.",
                "A beta above 1 generally implies higher market sensitivity; below 1 implies lower market sensitivity.",
            ]
        elif "concentration" in normalized:
            lines = [
                "Concentration risk means too much portfolio value is exposed to one stock, sector, theme, or macro factor.",
                "This agent flags sector concentration when one sector exceeds the configured 40% threshold.",
            ]
        else:
            lines = [
                "Finance covers how money is planned, raised, allocated, invested, and protected against risk.",
                "Ask about a specific concept, portfolio, stock, mutual fund, or market topic if you want a more targeted answer.",
            ]
        lines.append("This is an informational analysis based on the supplied data, not financial advice.")
        return "\n".join(lines)

    def _market_answer(self, market_summary: dict[str, Any], reasoning_chains: list[dict[str, Any]]) -> str:
        lines = [
            f"Market sentiment is {market_summary['sentiment'].lower()}. The tracked indices averaged "
            f"{market_summary['average_index_change_percent']}% today.",
        ]
        breadth = market_summary.get("market_breadth", {}).get("nifty50", {})
        if breadth:
            lines.append(
                f"Market breadth was weak: {breadth.get('advances')} advances versus "
                f"{breadth.get('declines')} declines in NIFTY 50."
            )
        fii = market_summary.get("fii_dii_data", {}).get("fii", {})
        if fii:
            lines.append(f"FIIs were net sellers of {fii.get('net_value_cr'):+,.0f} crore, adding risk-off pressure.")
        if reasoning_chains:
            lines.append("High-impact drivers:")
            seen_news: set[str] = set()
            for chain in reasoning_chains:
                news_id = chain.get("news_id")
                if news_id in seen_news:
                    continue
                seen_news.add(news_id)
                lines.append(f"- {chain['headline']} affected {chain.get('sector')} ({chain.get('sector_change_percent')}%).")
                if len(seen_news) == 3:
                    break
        lines.append("This is an informational analysis based on the supplied data, not financial advice.")
        return "\n".join(lines)

    def _estimate_token_usage(self, question: str, answer: str) -> dict[str, int]:
        prompt_tokens = max(1, len(question.split()))
        completion_tokens = max(1, len(answer.split()))
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    def _risk_answer(self, portfolio_analysis: dict[str, Any]) -> str:
        risk = portfolio_analysis.get("risk_metrics", {})
        allocation = portfolio_analysis.get("sector_allocation", {})
        lines = [
            f"Primary risk profile: {portfolio_analysis.get('risk_profile')} with "
            f"{risk.get('volatility', 'UNKNOWN').lower()} volatility and beta {risk.get('beta')}.",
            f"Largest sector exposure is {risk.get('largest_sector')} at {risk.get('largest_sector_weight')}%.",
        ]
        if risk.get("concentration_risk"):
            lines.append("Concentration risk is active because the largest sector exceeds the 40% threshold.")
        lines.append("Largest allocations:")
        for sector, weight in sorted(allocation.items(), key=lambda item: item[1], reverse=True)[:4]:
            lines.append(f"- {sector}: {weight}%")
        lines.append("This is an informational analysis based on the supplied data, not financial advice.")
        return "\n".join(lines)

    def _conflict_answer(self, reasoning_chains: list[dict[str, Any]]) -> str:
        conflicts = [chain for chain in reasoning_chains if chain.get("conflict")]
        if not conflicts:
            return (
                "I did not find a high-confidence conflict among the top-ranked portfolio drivers. "
                "The main signals and price moves are broadly aligned in the selected evidence.\n"
                "This is an informational analysis based on the supplied data, not financial advice."
            )

        lines = ["Conflicting signals found:"]
        for chain in conflicts[:3]:
            lines.append(
                f"- {chain.get('holding_id')} moved {chain.get('holding_day_change_percent')}% despite "
                f"{chain.get('news_sentiment', '').lower()} news: {chain.get('headline')}"
            )
        lines.append("This is an informational analysis based on the supplied data, not financial advice.")
        return "\n".join(lines)

    def _movers_answer(self, portfolio_analysis: dict[str, Any]) -> str:
        lines = ["Top portfolio movers today:"]
        lines.append("Largest detractors:")
        for holding in portfolio_analysis.get("top_detractors", [])[:3]:
            lines.append(
                f"- {holding.get('id')}: {holding.get('day_change_percent')}% "
                f"({holding.get('day_change'):+,.0f} INR)"
            )
        lines.append("Largest gainers:")
        for holding in portfolio_analysis.get("top_gainers", [])[:3]:
            lines.append(
                f"- {holding.get('id')}: {holding.get('day_change_percent')}% "
                f"({holding.get('day_change'):+,.0f} INR)"
            )
        lines.append("This is an informational analysis based on the supplied data, not financial advice.")
        return "\n".join(lines)
