"""Health check endpoint for the RAG service."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from cafetera_rag_service.models import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Check Qdrant connectivity and LLM availability."""
    rag_resources = request.app.state.rag_resources

    # Check Qdrant
    qdrant_status = "unavailable"
    if rag_resources.qdrant_client is not None:
        try:
            await rag_resources.qdrant_client.get_collections()
            qdrant_status = "ok"
        except Exception:
            logger.warning("Qdrant health check failed", exc_info=True)
            qdrant_status = "error"

    # Check LLM
    llm_status = "ok" if rag_resources.llm is not None else "unavailable"

    overall = "ok" if qdrant_status == "ok" and llm_status == "ok" else "degraded"
    return HealthResponse(status=overall, qdrant=qdrant_status, llm=llm_status)
