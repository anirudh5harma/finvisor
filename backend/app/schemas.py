from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    portfolio_id: str | None = None


class EvaluationResult(BaseModel):
    score: int
    flags: list[str] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    criteria_scores: dict[str, int] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    confidence_score: float
    reasoning_chains: list[dict[str, Any]]
    evidence: dict[str, Any]
    evaluation: EvaluationResult
    response_metadata: dict[str, Any] = Field(default_factory=dict)
