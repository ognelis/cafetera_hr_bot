"""Shared resource container and factory for the application.

This module consolidates initialization of shared resources (S3, Database,
RAGClient, CategoryFileService) used across admin and VK bot packages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from databases import Database

from cafetera_core.config import CoreSettings
from cafetera_core.domain.category_file_service import CategoryFileService
from cafetera_core.rag_client import RAGClient
from cafetera_core.storage.category_repo import CategoryFileRepository
from cafetera_core.storage.document_repo import DocumentRepository
from cafetera_core.storage.s3 import S3Storage

logger = logging.getLogger(__name__)


@dataclass
class AppResources:
    """Container for all shared application resources.

    All attributes are optional (None) by default and are initialized
    by build_resources(). This allows graceful degradation when
    certain services are unavailable.
    """

    settings: CoreSettings
    rag_client: RAGClient | None = None
    s3: S3Storage | None = None
    db: Database | None = None
    doc_repo: DocumentRepository | None = None
    category_file_repo: CategoryFileRepository | None = None
    category_file_service: CategoryFileService | None = None


async def build_resources(
    settings: CoreSettings, *, with_s3: bool = False, with_db: bool = False
) -> AppResources:
    """Build and initialize all application resources.

    Args:
        settings: Application settings.
        with_s3: Whether to initialize S3 storage.
        with_db: Whether to initialize Database and repositories.

    Returns:
        AppResources container with initialized resources.
    """
    res = AppResources(settings=settings)

    # 1. RAG client
    try:
        res.rag_client = RAGClient(
            base_url=settings.rag_service_url,
            api_key=settings.rag_service_api_key,
        )
        logger.info("RAG client configured (url=%s)", settings.rag_service_url)
    except Exception:
        logger.warning("RAG client not available", exc_info=True)
        res.rag_client = None

    # 2. S3 storage (if requested)
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

    # 3. Document repository and service (if requested)
    if with_db:
        try:
            db = Database(settings.database_url)
            await db.connect()
            res.db = db
            logger.info("Database connected")

            from cafetera_core.storage.database import init_db

            await init_db(db)
            logger.info("Database schema initialized")

            repo = DocumentRepository(db)
            res.doc_repo = repo
            logger.info("DocumentRepository initialized")

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

    return res


async def close_resources(res: AppResources) -> None:
    """Close all resources in the correct order.

    Closes resources with try/except per resource to ensure all cleanup
    is attempted even if individual resources fail to close.

    Args:
        res: AppResources container with resources to close.
    """
    # 1. Close RAG client if present
    if res.rag_client is not None:
        try:
            await res.rag_client.aclose()
        except Exception:
            logger.warning("Error closing RAG client", exc_info=True)

    # 2. Close S3 if present
    if res.s3 is not None:
        try:
            await res.s3.close()
        except Exception:
            logger.warning("Error closing S3 client", exc_info=True)

    # 3. Disconnect database if present
    if res.db is not None:
        try:
            await res.db.disconnect()
        except Exception:
            logger.warning("Error disconnecting database", exc_info=True)

    # 4. Set all fields to None
    res.rag_client = None
    res.s3 = None
    res.db = None
    res.doc_repo = None
    res.category_file_repo = None
    res.category_file_service = None
