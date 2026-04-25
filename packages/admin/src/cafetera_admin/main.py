"""FastAPI application entry point with lifespan resource management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cafetera_admin.config import AdminSettings
from cafetera_core.resources import build_resources, close_resources

logger = logging.getLogger(__name__)


def _resolve_repo_root() -> Path:
    """Find the repository root by walking up from this file.

    Looks for the directory containing ``packages/`` which is unique
    to the monorepo root.  Falls back to walking up until ``pyproject.toml``
    is found.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "packages").is_dir():
            return parent
        if (parent / "pyproject.toml").is_file() and (parent / "templates").is_dir():
            return parent
    # Fallback: 4 levels up from this file to repo root
    # (cafetera_admin/main.py -> src/ -> admin/ -> packages/ -> root)
    return current.parents[3]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: AdminSettings = app.state.settings

    res = await build_resources(settings, with_s3=True, with_db=True)

    # Store in app.state for FastAPI deps
    app.state.s3 = res.s3
    app.state.qdrant_client = res.qdrant_client
    app.state.embeddings = res.embeddings
    app.state.doc_repo = res.doc_repo
    app.state.doc_service = res.doc_service
    app.state.qa_service = res.qa_service
    app.state.category_file_service = res.category_file_service
    app.state.indexing_semaphore = asyncio.Semaphore(settings.max_concurrent_indexing)

    yield

    await close_resources(res)


def create_app(settings: AdminSettings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    if settings is None:
        settings = AdminSettings()

    app = FastAPI(
        title="Cafetera HR Bot Admin",
        lifespan=lifespan,
    )
    # Initialize state
    app.state.settings = settings

    # Static files — resolve from repo root since the package moved deeper
    repo_root = _resolve_repo_root()
    static_dir = repo_root / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Templates
    templates_dir = repo_root / "templates"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))

    # Routes
    from cafetera_admin.api.category_files import router as category_files_router
    from cafetera_admin.api.documents import router as documents_router

    app.include_router(documents_router)
    app.include_router(category_files_router)

    return app
