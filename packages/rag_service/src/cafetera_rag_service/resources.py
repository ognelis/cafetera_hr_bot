"""RAG resource container and factory for the RAG microservice.

Extracts RAG-relevant initialization from cafetera_core.resources
into a standalone factory for the RAG service.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cafetera_core.storage.s3 import S3Storage
from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.qa_service import QAService
from cafetera_rag_service.rag.chain import build_llm
from cafetera_rag_service.rag.reranker import CrossEncoderReranker
from cafetera_rag_service.rag.retriever import (
    build_embeddings,
    build_qdrant_client,
    build_sparse_embeddings,
)

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel
    from qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)


async def _ensure_collection(
    client: AsyncQdrantClient,
    embeddings: Embeddings,
    settings: RagServiceSettings,
    sparse_embedding=None,
) -> None:
    """Ensure the Qdrant collection exists, creating it if necessary.

    Creates the collection with named dense vector + optional BM25 sparse
    layout.  Reranking is handled downstream by the cross-encoder
    retriever wrapper, so the collection schema no longer varies.
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
        logger.info(
            "Hybrid search enabled - adding sparse vector configuration"
        )

    vectors_config: dict[str, models.VectorParams] = {
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
        "Created Qdrant collection '%s' with vector_size=%d, "
        "INT8 scalar quantization",
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

    # Create KEYWORD indexes for high-cardinality fields
    await client.create_payload_index(
        collection_name=collection_name,
        field_name="metadata.document_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    await client.create_payload_index(
        collection_name=collection_name,
        field_name="metadata.filename",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    await client.create_payload_index(
        collection_name=collection_name,
        field_name="metadata.headings",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    logger.info(
        "Created KEYWORD payload indexes on '%s.metadata.document_id', "
        "'%s.metadata.filename', and '%s.metadata.headings'",
        collection_name,
        collection_name,
        collection_name,
    )


def build_reranker(settings: RagServiceSettings) -> CrossEncoderReranker | None:
    """Build a cross-encoder reranker from settings.

    Returns ``None`` when reranking is disabled.
    """
    if not settings.reranking_enabled:
        return None

    logger.info(
        "Loading cross-encoder reranker (model=%s, top_n=%d)",
        settings.reranker_model,
        settings.reranker_top_n,
    )
    return CrossEncoderReranker(
        model_name=settings.reranker_model,
        top_n=settings.reranker_top_n,
    )


@dataclass
class RagResources:
    """Container for RAG-specific application resources.

    All attributes except settings are optional (None) by default and are
    initialized by build_rag_resources().  This allows graceful degradation
    when certain services are unavailable.
    """

    settings: RagServiceSettings
    qdrant_client: AsyncQdrantClient | None = None
    embeddings: Embeddings | None = None
    llm: BaseChatModel | None = None
    sparse_embeddings: object | None = None
    reranker: CrossEncoderReranker | None = None
    s3_storage: S3Storage | None = None


async def build_rag_resources(settings: RagServiceSettings) -> RagResources:
    """Build and initialize all RAG resources.

    Each major block is wrapped in try/except with logging for
    graceful degradation.
    """
    res = RagResources(settings=settings)

    # 1. Qdrant client and embeddings
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
                logger.warning(
                    "Error closing Qdrant client during init failure", exc_info=True
                )
            qdrant_client = None
        logger.warning(
            "Qdrant/embeddings not available — RAG operations will fail",
            exc_info=True,
        )
        res.qdrant_client = None
        res.embeddings = None
        res.sparse_embeddings = None

    # 2. Sparse embeddings for hybrid search (optional, degrades gracefully)
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

    # 3. Cross-encoder reranker (optional, degrades gracefully)
    if res.embeddings is not None:
        try:
            res.reranker = build_reranker(settings)
            if res.reranker is not None:
                logger.info("Cross-encoder reranker initialized")
        except Exception:
            logger.warning(
                "Reranker not available — falling back to dense+sparse",
                exc_info=True,
            )
            res.reranker = None

    # 4. Ensure collection exists and build LLM
    if qdrant_client is not None and embeddings is not None:
        try:
            await _ensure_collection(
                qdrant_client,
                embeddings,
                settings,
                sparse_embedding=res.sparse_embeddings,
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

    # 5. S3 storage (for document ingestion)
    try:
        res.s3_storage = S3Storage(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
        )
        logger.info("S3 storage initialized")
    except Exception:
        logger.warning("S3 storage not available — ingestion will fail", exc_info=True)
        res.s3_storage = None

    return res


async def close_rag_resources(res: RagResources) -> None:
    """Close all RAG resources in the correct order.

    Closes resources with try/except per resource to ensure all cleanup
    is attempted even if individual resources fail to close.
    """
    # Close S3 storage if present
    if res.s3_storage is not None:
        try:
            await res.s3_storage.close()
        except Exception:
            logger.warning("Error closing S3 storage", exc_info=True)

    # Close Qdrant client if present
    if res.qdrant_client is not None:
        try:
            await res.qdrant_client.close()
        except Exception:
            logger.warning("Error closing Qdrant client", exc_info=True)

    # Set all fields to None
    res.qdrant_client = None
    res.embeddings = None
    res.sparse_embeddings = None
    res.reranker = None
    res.llm = None
    res.s3_storage = None


def build_qa_service(
    res: RagResources,
    system_prompt: str,
    *,
    include_metadata: bool = False,
) -> QAService:
    """Create a QAService using the shared RAG resources.

    Raises:
        ValueError: If required resources (qdrant_client, embeddings, llm)
            are not initialized.
    """
    if (
        res.qdrant_client is None
        or res.embeddings is None
        or res.llm is None
    ):
        raise ValueError(
            "Cannot build QAService: required resources "
            "(qdrant_client, embeddings, llm) not initialized"
        )

    return QAService(
        qdrant_client=res.qdrant_client,
        embeddings=res.embeddings,
        llm=res.llm,
        settings=res.settings,
        global_system_prompt=system_prompt,
        include_metadata=include_metadata,
        sparse_embedding=res.sparse_embeddings,
        reranker=res.reranker,
    )
