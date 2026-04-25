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

from cafetera_core.config import CoreSettings
from cafetera_core.domain.category_file_service import CategoryFileService
from cafetera_core.domain.qa_service import QAService
from cafetera_core.rag.chain import build_llm
from cafetera_core.rag.colbert_embeddings import build_colbert_embeddings
from cafetera_core.rag.retriever import (
    build_embeddings,
    build_qdrant_client,
    build_sparse_embeddings,
)
from cafetera_core.storage.category_repo import CategoryFileRepository
from cafetera_core.storage.document_repo import DocumentRepository
from cafetera_core.storage.s3 import S3Storage

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel
    from qdrant_client import AsyncQdrantClient


async def _ensure_collection(
    client: AsyncQdrantClient,
    embeddings: Embeddings,
    settings: CoreSettings,
    sparse_embedding=None,
    colbert_embedding=None,
) -> None:
    """Ensure the Qdrant collection exists, creating it if necessary.

    This function checks if the collection exists and creates it with the
    correct vector configuration if it doesn't. This allows the QA service
    to initialize properly even on first startup before any documents are
    indexed.

    When reranking is enabled, the collection uses named vector spaces:
    ``"dense"``, ``"colbert"``, and ``"bm25"``.  Otherwise it uses
    named dense + ``"bm25"`` sparse layout.
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

    use_reranking = (
        settings.reranking_enabled
        and colbert_embedding is not None
    )

    if use_reranking:
        # Named vector config for hybrid reranking
        colbert_dim = colbert_embedding.dimension

        vectors_config: dict[str, models.VectorParams] | models.VectorParams = {
            "dense": models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8,
                        quantile=0.99,
                        always_ram=False,
                    ),
                ),
            ),
            "colbert": models.VectorParams(
                size=colbert_dim,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM,
                ),
                hnsw_config=models.HnswConfigDiff(m=0),
                on_disk=True,
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8,
                        quantile=0.99,
                        always_ram=False,
                    ),
                ),
            ),
        }
        sparse_vectors_config = {
            "bm25": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
                index=models.SparseIndexParams(on_disk=True),
            ),
        }
        logger.info(
            "Creating collection '%s' with reranking config "
            "(dense_dim=%d, colbert_dim=%d, bm25, INT8 quantization)",
            collection_name,
            vector_size,
            colbert_dim,
        )
    else:
        # Hybrid search: dense + sparse (bm25)
        dense_vector_config = models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=False,
                ),
            ),
        )
        sparse_vectors_config = None
        if sparse_embedding is not None:
            sparse_vectors_config = {
                "bm25": models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                    index=models.SparseIndexParams(on_disk=True),
                ),
            }
            logger.info("Hybrid search enabled - adding sparse vector configuration")

        vectors_config = {
            "dense": dense_vector_config,
        }

    # Create the collection with INT8 scalar quantization
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=vectors_config,
        sparse_vectors_config=sparse_vectors_config,
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=10000,
            deleted_threshold=0.2,
        ),
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(
                type=models.ScalarType.INT8,
                quantile=0.99,
                always_ram=False,
            ),
        ),
    )
    logger.info(
        "Created Qdrant collection '%s' with vector_size=%d, INT8 scalar quantization",
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

    Use ``build_qa_service()`` to create a QAService with a
    package-specific system prompt.
    """

    settings: CoreSettings
    qdrant_client: AsyncQdrantClient | None = None
    embeddings: Embeddings | None = None
    llm: BaseChatModel | None = None
    s3: S3Storage | None = None
    db: Database | None = None
    doc_repo: DocumentRepository | None = None
    sparse_embeddings: object | None = None
    colbert_embeddings: object | None = None
    category_file_repo: CategoryFileRepository | None = None
    category_file_service: CategoryFileService | None = None

    def build_qa_service(
        self,
        system_prompt: str,
        *,
        include_metadata: bool = False,
    ) -> QAService:
        """Create a QAService using the shared resources.

        Args:
            system_prompt: The system prompt for the QA chain.
            include_metadata: Whether to include document metadata in answers.

        Returns:
            A fully initialized QAService.

        Raises:
            ValueError: If required resources (qdrant_client, embeddings,
                llm, settings) are not initialized.
        """
        if (
            self.qdrant_client is None
            or self.embeddings is None
            or self.llm is None
            or self.settings is None
        ):
            raise ValueError(
                "Cannot build QAService: required resources "
                "(qdrant_client, embeddings, llm, settings) not initialized"
            )

        return QAService(
            qdrant_client=self.qdrant_client,
            embeddings=self.embeddings,
            llm=self.llm,
            settings=self.settings,
            global_system_prompt=system_prompt,
            include_metadata=include_metadata,
            sparse_embedding=self.sparse_embeddings,
            colbert_embedding=self.colbert_embeddings,
        )


async def build_resources(
    settings: CoreSettings, *, with_s3: bool = False, with_db: bool = False
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

    # 2c. ColBERT embeddings for reranking (optional, degrades gracefully)
    if res.embeddings is not None:
        try:
            res.colbert_embeddings = build_colbert_embeddings(settings)
            if res.colbert_embeddings is not None:
                logger.info("ColBERT embeddings initialized (reranking enabled)")
        except Exception:
            logger.warning(
                "ColBERT embeddings not available — falling back to dense+sparse",
                exc_info=True,
            )
            res.colbert_embeddings = None

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

    # 4. LLM (QAService creation is deferred to each package via build_qa_service)
    if qdrant_client is not None and embeddings is not None:
        try:
            # Ensure collection exists before any retriever usage
            await _ensure_collection(
                qdrant_client,
                embeddings,
                settings,
                sparse_embedding=res.sparse_embeddings,
                colbert_embedding=res.colbert_embeddings,
            )

            llm = build_llm(settings)
            res.llm = llm
            logger.info("LLM initialized successfully")
        except Exception:
            logger.warning(
                "LLM not available — QA service creation will fail",
                exc_info=True,
            )
            res.llm = None

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
    res.colbert_embeddings = None
    res.llm = None
    res.doc_repo = None
    res.category_file_repo = None
    res.category_file_service = None
