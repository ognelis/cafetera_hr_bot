"""FastAPI application entry point with lifespan resource management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Settings
from app.integrations.vk.handlers import set_qa_service
from app.resources import build_resources, close_resources
from app.storage.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings

    # Initialise SQLite
    await init_db(settings.db_path)

    res = await build_resources(settings, with_s3=True, with_db=True)

    # Store in app.state for FastAPI deps
    app.state.s3 = res.s3
    app.state.qdrant_client = res.qdrant_client
    app.state.embeddings = res.embeddings
    app.state.doc_repo = res.doc_repo
    app.state.doc_service = res.doc_service
    app.state.qa_service = res.qa_service
    app.state.indexing_semaphore = asyncio.Semaphore(settings.max_concurrent_indexing)

    # VK handler globals
    if res.qa_service:
        set_qa_service(res.qa_service)

    yield

    await close_resources(res)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Cafetera HR Bot Admin",
        lifespan=lifespan,
    )
    # Initialize state
    app.state.settings = settings

    # Static files
    static_dir = Path(__file__).resolve().parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Templates
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))

    # Routes
    from app.api.documents import router as documents_router

    app.include_router(documents_router)

    return app
