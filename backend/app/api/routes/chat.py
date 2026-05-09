from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dependencies import get_chat_agent
from ...schemas import ChatRequest, ChatResponse
from ...telemetry.langfuse import trace


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
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
