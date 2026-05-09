from __future__ import annotations

from fastapi import APIRouter

from ...telemetry.langfuse import observability_status


router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/status")
def get_observability_status() -> dict:
    return observability_status()
