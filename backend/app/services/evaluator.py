from __future__ import annotations

from .intent_router import ChatIntent
from ..schemas import EvaluationResult


class ResponseEvaluator:
    def evaluate(
        self,
        answer: str,
        has_portfolio: bool,
        reasoning_chains: list[dict],
        evidence: dict,
        intent: ChatIntent = ChatIntent.PORTFOLIO_IMPACT,
    ) -> EvaluationResult:
        missing: list[str] = []
        flags: list[str] = []

        if intent in {ChatIntent.MARKET_SUMMARY, ChatIntent.STOCK_ANALYSIS, ChatIntent.MUTUAL_FUND_ANALYSIS, ChatIntent.GENERAL_FINANCE}:
            has_portfolio = False

        if has_portfolio and "portfolio" not in answer.lower():
            missing.append("portfolio impact")
        if intent in {ChatIntent.PORTFOLIO_IMPACT, ChatIntent.MARKET_SUMMARY} and not reasoning_chains:
            missing.append("causal chain")
        if intent in {ChatIntent.PORTFOLIO_IMPACT, ChatIntent.MARKET_SUMMARY, ChatIntent.STOCK_ANALYSIS} and not evidence.get("news_ids"):
            missing.append("news evidence")
        if intent in {ChatIntent.PORTFOLIO_IMPACT, ChatIntent.MARKET_SUMMARY, ChatIntent.STOCK_ANALYSIS} and not evidence.get("sectors"):
            missing.append("sector context")
        if has_portfolio and intent != ChatIntent.MARKET_SUMMARY and not evidence.get("symbols"):
            missing.append("holding context")
        if intent == ChatIntent.CONFLICT_ANALYSIS and not any(chain.get("conflict") for chain in reasoning_chains):
            missing.append("conflict evidence")
        if any(chain.get("conflict") for chain in reasoning_chains) and "conflict" not in answer.lower() and "despite" not in answer.lower():
            flags.append("conflict not clearly explained")
        if "not financial advice" not in answer.lower():
            flags.append("missing financial advice disclaimer")

        criteria_scores = {
            "causal_linking": self._score_causal_linking(reasoning_chains, intent),
            "evidence_grounding": 100 if evidence.get("news_ids") else 55,
            "portfolio_specificity": 100 if not has_portfolio or evidence.get("symbols") else 60,
            "conflict_handling": self._score_conflict_handling(answer, reasoning_chains, intent),
            "answer_safety": 100 if "not financial advice" in answer.lower() else 60,
        }
        score = 100
        score -= len(missing) * 12
        score -= len(flags) * 8
        score = min(score, round(sum(criteria_scores.values()) / len(criteria_scores)))
        score = max(score, 0)

        return EvaluationResult(score=score, flags=flags, missing_elements=missing, criteria_scores=criteria_scores)

    def _score_causal_linking(self, reasoning_chains: list[dict], intent: ChatIntent) -> int:
        if intent in {ChatIntent.STOCK_ANALYSIS, ChatIntent.MUTUAL_FUND_ANALYSIS, ChatIntent.GENERAL_FINANCE}:
            return 90
        if not reasoning_chains:
            return 50
        complete = [
            chain
            for chain in reasoning_chains
            if chain.get("news_id") and chain.get("sector") and (chain.get("holding_id") or intent == ChatIntent.MARKET_SUMMARY)
        ]
        return 100 if len(complete) == len(reasoning_chains) else 75

    def _score_conflict_handling(self, answer: str, reasoning_chains: list[dict], intent: ChatIntent) -> int:
        has_conflict = any(chain.get("conflict") for chain in reasoning_chains)
        if intent == ChatIntent.CONFLICT_ANALYSIS:
            return 100 if has_conflict and ("despite" in answer.lower() or "conflict" in answer.lower()) else 55
        if has_conflict:
            return 90 if ("despite" in answer.lower() or "conflict" in answer.lower()) else 70
        return 100
