"""FastAPI application entry point with lifespan resource management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cafetera_admin.api.deps import AuthRedirectException
from cafetera_admin.config import AdminSettings
from cafetera_admin.domain.document_service import DocumentService
from cafetera_admin.parser import ensure_models_cached
from cafetera_admin.prompts import GLOBAL_EXPERTS_PROMPT
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

    # Ensure tokenizer and Docling models are cached before any document
    # parsing, then enable HuggingFace offline mode. This is a blocking call
    # that may download files on first run, so we run it in a thread.
    await asyncio.to_thread(ensure_models_cached, settings.chunker_tokenizer_model)

    res = await build_resources(settings, with_s3=True, with_db=True)

    # Store in app.state for FastAPI deps
    app.state.s3 = res.s3
    app.state.qdrant_client = res.qdrant_client
    app.state.embeddings = res.embeddings
    app.state.doc_repo = res.doc_repo

    if (
        res.doc_repo is not None
        and res.qdrant_client is not None
        and res.embeddings is not None
    ):
        app.state.doc_service = DocumentService(
            repo=res.doc_repo,
            qdrant_client=res.qdrant_client,
            embeddings=res.embeddings,
            collection_name=settings.qdrant_collection,
            sparse_embedding=res.sparse_embeddings,
            colbert_embedding=res.colbert_embeddings,
        )
    else:
        app.state.doc_service = None

    if (
        res.qdrant_client is not None
        and res.embeddings is not None
        and res.llm is not None
    ):
        app.state.qa_service = res.build_qa_service(GLOBAL_EXPERTS_PROMPT)
    else:
        app.state.qa_service = None

    app.state.category_file_service = res.category_file_service
    app.state.indexing_semaphore = asyncio.Semaphore(settings.max_concurrent_indexing)

    yield

    await close_resources(res)


def _auth_redirect_handler(_request: Request, exc: Exception) -> Response:
    """Convert AuthRedirectException into the appropriate redirect response."""
    assert isinstance(exc, AuthRedirectException)
    if exc.is_htmx:
        return Response(status_code=200, headers={"HX-Redirect": "/login"})
    return RedirectResponse(url="/login", status_code=303)


def create_app(settings: AdminSettings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    if settings is None:
        settings = AdminSettings()

    app = FastAPI(
        title="Cafetera HR Bot Admin",
        lifespan=lifespan,
    )
    app.add_exception_handler(AuthRedirectException, _auth_redirect_handler)

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
