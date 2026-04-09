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

from app.config import Settings
from app.domain.document_service import DocumentService
from app.domain.qa_service import QAService
from app.rag.chain import build_llm, build_rag_chain
from app.rag.prompts import GLOBAL_EXPERTS_PROMPT
from app.rag.retriever import build_embeddings, build_qdrant_client, build_retriever
from app.storage.document_repo import DocumentRepository
from app.storage.s3 import S3Storage

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel
    from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


@dataclass
class AppResources:
    """Container for all shared application resources.

    All attributes are optional (None) by default and are initialized
    by build_resources(). This allows graceful degradation when
    certain services are unavailable.
    """

    settings: Settings
    qdrant_client: QdrantClient | None = None
    embeddings: Embeddings | None = None
    llm: BaseChatModel | None = None
    s3: S3Storage | None = None
    doc_repo: DocumentRepository | None = None
    doc_service: DocumentService | None = None
    qa_service: QAService | None = None


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
            await s3.open()
            res.s3 = s3
            logger.info("S3 storage connected (bucket=%s)", settings.s3_bucket)
        except Exception:
            logger.warning(
                "S3 storage not available — upload/download will fail",
                exc_info=True,
            )
            res.s3 = None

    # 2. Qdrant client and embeddings
    qdrant_client: QdrantClient | None = None
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
                qdrant_client.close()
            except Exception:
                logger.warning("Error closing Qdrant client during init failure", exc_info=True)
            qdrant_client = None
        logger.warning(
            "Qdrant/embeddings not available — document operations will fail",
            exc_info=True,
        )
        res.qdrant_client = None
        res.embeddings = None

    # 3. Document repository and service (if requested)
    if with_db:
        try:
            repo = DocumentRepository(settings.db_path)
            res.doc_repo = repo
            logger.info("DocumentRepository initialized")

            if qdrant_client is not None and embeddings is not None:
                doc_service = DocumentService(
                    repo=repo,
                    qdrant_client=qdrant_client,
                    embeddings=embeddings,
                    collection_name=settings.qdrant_collection,
                )
                res.doc_service = doc_service
                logger.info("DocumentService initialized")
        except Exception:
            logger.warning(
                "Document repository/service not available",
                exc_info=True,
            )

    # 4. LLM, retriever, chain, and QA service
    if qdrant_client is not None and embeddings is not None:
        try:
            llm = build_llm(settings)
            res.llm = llm

            retriever = build_retriever(
                settings,
                qdrant_client=qdrant_client,
                embeddings=embeddings,
            )
            chain = build_rag_chain(retriever, llm, system_prompt=GLOBAL_EXPERTS_PROMPT)

            qa_service = QAService(
                chain=chain,
                qdrant_client=qdrant_client,
                embeddings=embeddings,
                llm=llm,
                settings=settings,
            )
            res.qa_service = qa_service
            logger.info("QA service initialized successfully")
        except Exception:
            logger.warning(
                "QA service not available — handlers will use fallback",
                exc_info=True,
            )
            res.qa_service = None
    else:
        res.qa_service = None

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
            res.qdrant_client.close()
        except Exception:
            logger.warning("Error closing Qdrant client", exc_info=True)

    # 3. Set all fields to None
    res.s3 = None
    res.qdrant_client = None
    res.embeddings = None
    res.llm = None
    res.doc_repo = None
    res.doc_service = None
    res.qa_service = None
