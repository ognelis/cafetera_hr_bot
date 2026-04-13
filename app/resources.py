"""Shared resource container and factory for RAG application.

This module consolidates initialization of RAG resources (Qdrant client,
embeddings, LLM, retriever, chain, QAService, S3, DocumentRepository,
DocumentService) that was previously duplicated between app/main.py and
scripts/polling_vk.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from databases import Database

from app.config import Settings
from app.domain.category_file_service import CategoryFileService
from app.domain.document_service import DocumentService
from app.domain.qa_service import QAService
from app.rag.chain import build_llm, build_rag_chain
from app.rag.prompts import GLOBAL_EXPERTS_PROMPT, SYSTEM_PROMPT
from app.rag.retriever import (
    CollectionNotFoundError,
    build_embeddings,
    build_qdrant_client,
    build_retriever,
    build_sparse_embeddings,
)
from app.storage.category_repo import CategoryFileRepository
from app.storage.document_repo import DocumentRepository
from app.storage.s3 import S3Storage

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel
    from qdrant_client import AsyncQdrantClient


async def _ensure_collection(
    client: AsyncQdrantClient,
    embeddings: Embeddings,
    settings: Settings,
    sparse_embedding=None,
) -> None:
    """Ensure the Qdrant collection exists, creating it if necessary.

    This function checks if the collection exists and creates it with the
    correct vector configuration if it doesn't. This allows the QA service
    to initialize properly even on first startup before any documents are
    indexed.
    """
    from qdrant_client import models

    collection_name = settings.qdrant_collection

    # Check if collection already exists
    if await client.collection_exists(collection_name):
        logger.info("Qdrant collection '%s' already exists", collection_name)
        return

    # Collection doesn't exist - need to create it
    logger.info("Qdrant collection '%s' not found - creating it", collection_name)

    # Get embedding dimensions by doing a test embed
    try:
        test_embedding = embeddings.embed_documents(["test"])
        vector_size = len(test_embedding[0])
    except Exception as exc:
        logger.warning("Failed to get embedding dimensions: %s", exc)
        raise

    # Build vector parameters
    vectors_config = models.VectorParams(
        size=vector_size,
        distance=models.Distance.COSINE,
    )

    # Build sparse vector config for hybrid search if enabled
    sparse_vectors_config = None
    if settings.retrieval_mode == "hybrid" and sparse_embedding is not None:
        sparse_vectors_config = {
            "text-sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(
                    on_disk=False,
                ),
            )
        }
        logger.info("Hybrid search enabled - adding sparse vector configuration")

    # Create the collection
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=vectors_config,
        sparse_vectors_config=sparse_vectors_config,
    )
    logger.info(
        "Created Qdrant collection '%s' with vector_size=%d",
        collection_name,
        vector_size,
    )
    # Create payload index for frequently filtered boolean field
    await client.create_payload_index(
        collection_name=collection_name,
        field_name="is_search_enabled",
        field_schema=models.PayloadSchemaType.BOOL,
    )
    logger.info(
        "Created BOOL payload index on '%s.is_search_enabled'",
        collection_name,
    )

logger = logging.getLogger(__name__)


@dataclass
class AppResources:
    """Container for all shared application resources.

    All attributes are optional (None) by default and are initialized
    by build_resources(). This allows graceful degradation when
    certain services are unavailable.
    """

    settings: Settings
    qdrant_client: AsyncQdrantClient | None = None
    embeddings: Embeddings | None = None
    llm: BaseChatModel | None = None
    s3: S3Storage | None = None
    db: Database | None = None
    doc_repo: DocumentRepository | None = None
    doc_service: DocumentService | None = None
    qa_service: QAService | None = None
    vk_qa_service: QAService | None = None
    sparse_embeddings: object | None = None
    category_file_repo: CategoryFileRepository | None = None
    category_file_service: CategoryFileService | None = None


async def build_resources(
    settings: Settings, *, with_s3: bool = False, with_db: bool = False
) -> AppResources:
    """Build and initialize all application resources.

    This factory replicates the initialization logic from app/main.py lifespan.
    Each major block (S3, Qdrant+embeddings, QA) is wrapped in try/except
    with logging for graceful degradation.

    Args:
        settings: Application settings.
        with_s3: Whether to initialize S3 storage.
        with_db: Whether to initialize DocumentRepository and DocumentService.

    Returns:
        AppResources container with initialized resources.
    """
    res = AppResources(settings=settings)

    # 1. S3 storage (if requested)
    if with_s3:
        try:
            s3 = S3Storage(
                endpoint_url=settings.s3_endpoint_url,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key,
                bucket=settings.s3_bucket,
            )
            res.s3 = s3
            logger.info(
                "S3 storage configured (bucket=%s) — will connect lazily",
                settings.s3_bucket,
            )
        except Exception:
            logger.warning(
                "S3 storage not available — upload/download will fail",
                exc_info=True,
            )
            res.s3 = None

    # 2. Qdrant client and embeddings
    qdrant_client: AsyncQdrantClient | None = None
    embeddings: Embeddings | None = None
    try:
        qdrant_client = build_qdrant_client(settings)
        embeddings = build_embeddings(settings)
        res.qdrant_client = qdrant_client
        res.embeddings = embeddings
        logger.info("Qdrant client and embeddings initialized")
    except Exception:
        if qdrant_client is not None:
            try:
                await qdrant_client.close()
            except Exception:
                logger.warning("Error closing Qdrant client during init failure", exc_info=True)
            qdrant_client = None
        logger.warning(
            "Qdrant/embeddings not available — document operations will fail",
            exc_info=True,
        )
        res.qdrant_client = None
        res.embeddings = None
        res.sparse_embeddings = None

    # 2b. Sparse embeddings for hybrid search (optional, degrades gracefully)
    if res.embeddings is not None:
        try:
            res.sparse_embeddings = build_sparse_embeddings(settings)
            if res.sparse_embeddings is not None:
                logger.info("Sparse embeddings initialized (hybrid search enabled)")
        except Exception:
            logger.warning(
                "Sparse embeddings not available — falling back to dense search",
                exc_info=True,
            )
            res.sparse_embeddings = None

    # 3. Document repository and service (if requested)
    if with_db:
        try:
            db = Database(settings.database_url)
            await db.connect()
            res.db = db
            logger.info("Database connected")

            from app.storage.database import init_db

            await init_db(db)
            logger.info("Database schema initialized")

            repo = DocumentRepository(db)
            res.doc_repo = repo
            logger.info("DocumentRepository initialized")

            if qdrant_client is not None and embeddings is not None:
                doc_service = DocumentService(
                    repo=repo,
                    qdrant_client=qdrant_client,
                    embeddings=embeddings,
                    collection_name=settings.qdrant_collection,
                    sparse_embedding=res.sparse_embeddings,
                )
                res.doc_service = doc_service
                logger.info("DocumentService initialized")

            # Initialize category file repository and service
            category_file_repo = CategoryFileRepository(db)
            res.category_file_repo = category_file_repo
            logger.info("CategoryFileRepository initialized")

            if res.s3 is not None:
                category_file_service = CategoryFileService(
                    repo=category_file_repo,
                    s3=res.s3,
                )
                res.category_file_service = category_file_service
                logger.info("CategoryFileService initialized")
        except Exception:
            logger.warning(
                "Document repository/service not available",
                exc_info=True,
            )

    # 4. LLM, retriever, chain, and QA service
    if qdrant_client is not None and embeddings is not None:
        try:
            # Ensure collection exists before building retriever
            await _ensure_collection(
                qdrant_client,
                embeddings,
                settings,
                sparse_embedding=res.sparse_embeddings,
            )

            llm = build_llm(settings)
            res.llm = llm

            retriever = build_retriever(
                settings,
                qdrant_client=qdrant_client,
                embeddings=embeddings,
                sparse_embedding=res.sparse_embeddings,
            )
            chain = build_rag_chain(retriever, llm, system_prompt=GLOBAL_EXPERTS_PROMPT)

            qa_service = QAService(
                chain=chain,
                qdrant_client=qdrant_client,
                embeddings=embeddings,
                llm=llm,
                settings=settings,
                global_system_prompt=GLOBAL_EXPERTS_PROMPT,
                include_metadata=True,
                sparse_embedding=res.sparse_embeddings,
            )
            res.qa_service = qa_service

            # Create VK QAService with strict SYSTEM_PROMPT
            vk_qa_service = QAService(
                qdrant_client=qdrant_client,
                embeddings=embeddings,
                llm=llm,
                settings=settings,
                global_system_prompt=SYSTEM_PROMPT,
                sparse_embedding=res.sparse_embeddings,
            )
            res.vk_qa_service = vk_qa_service
            logger.info("QA service initialized successfully")
        except CollectionNotFoundError:
            logger.info(
                "QA service not available — Qdrant collection not found. "
                "Upload and index a document to enable Q&A."
            )
            res.qa_service = None
            res.vk_qa_service = None
        except Exception:
            logger.warning(
                "QA service not available — handlers will use fallback",
                exc_info=True,
            )
            res.qa_service = None
            res.vk_qa_service = None
    else:
        res.qa_service = None
        res.vk_qa_service = None

    return res


async def close_resources(res: AppResources) -> None:
    """Close all resources in the correct order.

    Closes resources with try/except per resource to ensure all cleanup
    is attempted even if individual resources fail to close.

    Important: Do NOT call qa_service.close() — QAService no longer owns
    Qdrant lifecycle. The Qdrant client is closed directly here.

    Args:
        res: AppResources container with resources to close.
    """
    # 1. Close S3 if present
    if res.s3 is not None:
        try:
            await res.s3.close()
        except Exception:
            logger.warning("Error closing S3 client", exc_info=True)

    # 2. Close Qdrant client if present
    if res.qdrant_client is not None:
        try:
            await res.qdrant_client.close()
        except Exception:
            logger.warning("Error closing Qdrant client", exc_info=True)

    # 3. Disconnect database if present
    if res.db is not None:
        try:
            await res.db.disconnect()
        except Exception:
            logger.warning("Error disconnecting database", exc_info=True)

    # 4. Set all fields to None
    res.s3 = None
    res.db = None
    res.qdrant_client = None
    res.embeddings = None
    res.sparse_embeddings = None
    res.llm = None
    res.doc_repo = None
    res.doc_service = None
    res.qa_service = None
    res.vk_qa_service = None
    res.category_file_repo = None
    res.category_file_service = None
