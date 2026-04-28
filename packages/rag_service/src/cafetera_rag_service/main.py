"""FastAPI application entry point with lifespan resource management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.resources import build_rag_resources, close_rag_resources

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = RagServiceSettings()
    if not settings.rag_service_api_key:
        logger.warning(
            "RAG_SERVICE_API_KEY is not set — API is unauthenticated! "
            "Set it in .env for production."
        )

    # Cache Docling models and tokenizer (blocking, run in thread)
    from cafetera_rag_service.parser import ensure_models_cached

    await asyncio.to_thread(ensure_models_cached, settings.chunker_tokenizer_model)

    res = await build_rag_resources(settings)
    app.state.rag_resources = res
    app.state.settings = settings
    app.state.qa_services = {}  # cache: (prompt_hash, include_metadata) -> QAService
    yield
    await close_rag_resources(res)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(title="Cafetera RAG Service", lifespan=lifespan)

    from cafetera_rag_service.api.health import router as health_router
    from cafetera_rag_service.api.indexing import router as indexing_router
    from cafetera_rag_service.api.ingest import router as ingest_router
    from cafetera_rag_service.api.qa import router as qa_router

    app.include_router(health_router)
    app.include_router(qa_router)
    app.include_router(indexing_router)
    app.include_router(ingest_router)

    return app
