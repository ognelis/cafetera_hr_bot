"""FastAPI application entry point with lifespan resource management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Settings
from app.domain.document_service import DocumentService
from app.domain.qa_service import QAService
from app.integrations.vk.handlers import set_qa_service
from app.rag.chain import build_llm, build_rag_chain
from app.rag.prompts import GLOBAL_EXPERTS_PROMPT
from app.rag.retriever import build_embeddings, build_qdrant_client, build_retriever
from app.storage.database import init_db
from app.storage.document_repo import DocumentRepository
from app.storage.s3 import S3Storage

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """Typed application state for FastAPI app.state.

    All attributes are optional (None) by default and are initialized
    during application lifespan.
    """

    settings: Settings = field(default_factory=Settings)
    templates: Jinja2Templates | None = None
    s3: S3Storage | None = None
    qdrant_client: QdrantClient | None = None
    embeddings: Embeddings | None = None
    doc_repo: DocumentRepository | None = None
    doc_service: DocumentService | None = None
    qa_service: QAService | None = None
    indexing_semaphore: asyncio.Semaphore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings

    # Initialise SQLite
    await init_db(settings.db_path)

    # S3 storage
    s3: S3Storage | None = None
    try:
        s3 = S3Storage(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
        )
        await s3.open()
        app.state.s3 = s3
        logger.info("S3 storage connected (bucket=%s)", settings.s3_bucket)
    except Exception:
        logger.warning(
            "S3 storage not available — upload/download will fail",
            exc_info=True,
        )
        app.state.s3 = None

    # Qdrant client
    from qdrant_client import QdrantClient

    qdrant_client: QdrantClient | None = None
    try:
        qdrant_client = build_qdrant_client(settings)
        embeddings = build_embeddings(settings)

        repo = DocumentRepository(settings.db_path)
        doc_service = DocumentService(
            repo=repo,
            qdrant_client=qdrant_client,
            embeddings=embeddings,
            collection_name=settings.qdrant_collection,
        )
        app.state.qdrant_client = qdrant_client
        app.state.embeddings = embeddings
        app.state.doc_repo = repo
        app.state.doc_service = doc_service
        logger.info("Qdrant client and document service initialised")
    except Exception:
        if qdrant_client is not None:
            qdrant_client.close()
            qdrant_client = None
        logger.warning(
            "Qdrant/embeddings not available — document operations will fail",
            exc_info=True,
        )
        # Still create repo so list/metadata operations work
        repo = DocumentRepository(settings.db_path)
        app.state.qdrant_client = None
        app.state.embeddings = None
        app.state.doc_repo = repo
        app.state.doc_service = None

    # Semaphore to limit concurrent document indexing
    app.state.indexing_semaphore = asyncio.Semaphore(settings.max_concurrent_indexing)

    # QA service (for document-scoped questions in admin UI)
    # Create shared resources ONCE and pass to both DocumentService and QAService
    qa_service_instance: QAService | None = None
    if qdrant_client is not None:
        try:
            llm = build_llm(settings)
            retriever = build_retriever(
                settings,
                qdrant_client=qdrant_client,
                embeddings=embeddings,
            )
            chain = build_rag_chain(retriever, llm, system_prompt=GLOBAL_EXPERTS_PROMPT)
            qa_service_instance = QAService(
                chain=chain,
                qdrant_client=qdrant_client,
                embeddings=embeddings,
                llm=llm,
                settings=settings,
            )
            # Set module-level singleton for backward compat (VK handlers use qa_service.ask())
            set_qa_service(qa_service_instance)
            app.state.qa_service = qa_service_instance
            logger.info("QA service initialised successfully")
        except Exception:
            logger.warning("QA service not available — handlers will use fallback", exc_info=True)
            app.state.qa_service = None
    else:
        app.state.qa_service = None

    yield

    # Teardown
    if s3 is not None:
        try:
            await s3.close()
        except Exception:
            logger.warning("Error closing S3 client", exc_info=True)

    # Close QA service (but NOT the shared qdrant_client - that will be closed below)
    if qa_service_instance is not None:
        # Set _qdrant_client to None to prevent double-close since we close it below
        qa_service_instance._qdrant_client = None
        qa_service_instance.close()

    if qdrant_client is not None:
        try:
            qdrant_client.close()
        except Exception:
            logger.warning("Error closing Qdrant client", exc_info=True)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Cafetera HR Bot Admin",
        lifespan=lifespan,
    )
    # Initialize typed state
    app.state = AppState(settings=settings)

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
