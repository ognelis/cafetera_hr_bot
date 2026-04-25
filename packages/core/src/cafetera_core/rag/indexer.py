"""Qdrant chunk indexing and management operations.

Provides per-document operations: index, delete, toggle search, count,
and collection optimization.
Used by ``DocumentService`` in the domain layer.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any

from qdrant_client import models
from qdrant_client.async_qdrant_client import AsyncQdrantClient

if TYPE_CHECKING:
    from langchain_core.documents import Document as LCDocument
    from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


def prepare_chunks(
    chunks: list[LCDocument],
    *,
    document_id: str,
    filename: str,
    s3_key: str,
    is_search_enabled: bool = True,
) -> list[LCDocument]:
    """Enrich chunk metadata with document-level fields and unique ``chunk_id``.

    Original chunk metadata (``source``, ``section``, etc.) is preserved.
    """
    enriched: list[LCDocument] = []
    for chunk in chunks:
        meta = {
            **chunk.metadata,
            "document_id": document_id,
            "chunk_id": uuid.uuid4().hex,
            "filename": filename,
            "s3_key": s3_key,
            "is_search_enabled": is_search_enabled,
        }
        enriched.append(chunk.model_copy(update={"metadata": meta}))
    return enriched


async def index_chunks(
    client: AsyncQdrantClient,
    embeddings: Embeddings,
    collection_name: str,
    chunks: list[LCDocument],
    sparse_embedding=None,
    colbert_embedding=None,
) -> int:
    """Add pre-prepared chunks to the Qdrant collection.

    The collection must already exist.  Returns the number of indexed chunks.

    When ``colbert_embedding`` is provided, each point stores three vector
    spaces: ``"dense"``, ``"bm25"``, and ``"colbert"``.  Otherwise stores
    ``"dense"`` + optional ``"bm25"`` sparse.
    """
    if not chunks:
        return 0

    # Compute embeddings for all chunks
    texts = [chunk.page_content for chunk in chunks]
    vectors = embeddings.embed_documents(texts)

    # Compute sparse embeddings if provided
    sparse_vectors = None
    if sparse_embedding is not None:
        sparse_vectors = sparse_embedding.embed_documents(texts)

    # Compute ColBERT embeddings if provided
    colbert_vectors = None
    if colbert_embedding is not None:
        colbert_vectors = colbert_embedding.embed_documents(texts)

    # Build points for upsert — collection always uses named vectors:
    # "dense" + optional "bm25" + optional "colbert"
    use_colbert = colbert_vectors is not None
    use_sparse = sparse_vectors is not None
    points = []
    for i, chunk in enumerate(chunks):
        point_id = chunk.metadata.get("chunk_id", uuid.uuid4().hex)
        # Extract is_search_enabled and store as top-level field (no dotted key)
        # to avoid Qdrant's inconsistent dot interpretation across operations
        clean_meta = {k: v for k, v in chunk.metadata.items() if k != "is_search_enabled"}
        is_search_enabled = chunk.metadata.get("is_search_enabled", True)
        payload = {
            "page_content": chunk.page_content,
            "metadata": clean_meta,
            "is_search_enabled": is_search_enabled,
        }

        # Always use named vector layout matching collection's vectors_config
        vector: dict[str, Any] = {
            "dense": vectors[i],
        }
        if use_sparse:
            sv = sparse_vectors[i]
            indices = sv.indices.tolist() if hasattr(sv.indices, "tolist") else sv.indices
            values = sv.values.tolist() if hasattr(sv.values, "tolist") else sv.values
            vector["bm25"] = models.SparseVector(
                indices=indices,
                values=values,
            )
        if use_colbert:
            assert colbert_vectors is not None  # guaranteed by use_colbert
            vector["colbert"] = colbert_vectors[i]

        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    # Upsert to Qdrant
    await client.upsert(
        collection_name=collection_name,
        points=points,
    )

    logger.info("Indexed %d chunk(s) in '%s'", len(chunks), collection_name)
    return len(chunks)


async def delete_document_chunks(
    client: AsyncQdrantClient,
    collection_name: str,
    document_id: str,
) -> None:
    """Delete all vector chunks belonging to the given document."""
    await client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )
    logger.info(
        "Deleted chunks for document_id=%s from '%s'",
        document_id,
        collection_name,
    )


async def set_search_enabled(
    client: AsyncQdrantClient,
    collection_name: str,
    document_id: str,
    *,
    enabled: bool,
) -> None:
    """Update ``is_search_enabled`` on all chunks of a document.

    Uses Qdrant dot-notation payload update so other metadata fields
    are not affected.
    """
    await client.set_payload(
        collection_name=collection_name,
        payload={"is_search_enabled": enabled},
        points=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )
    logger.info(
        "Set is_search_enabled=%s for document_id=%s in '%s'",
        enabled,
        document_id,
        collection_name,
    )


async def count_document_chunks(
    client: AsyncQdrantClient,
    collection_name: str,
    document_id: str,
) -> int:
    """Return the number of chunks belonging to a document in Qdrant."""
    result = await client.count(
        collection_name=collection_name,
        count_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        ),
    )
    return result.count


async def optimize_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    *,
    indexing_threshold: int = 10000,
) -> None:
    """Trigger segment optimization on a Qdrant collection.

    Temporarily sets ``indexing_threshold`` to 0 to force the optimizer
    to merge all small segments into fewer larger ones.  This reduces
    storage overhead (especially for sparse BM25 vectors which allocate
    a full ``page_0.dat`` per segment) and improves query performance.

    After optimization completes, the original ``indexing_threshold`` is
    restored so that future writes do not trigger unnecessary merges.
    """
    # Force optimization by setting indexing_threshold to 0
    # Note: vacuum_min_vector_number has a hard minimum of 100 in Qdrant,
    # so optimization only works for collections with 100+ vectors.
    await client.update_collection(
        collection_name=collection_name,
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=0,
        ),
    )
    logger.info(
        "Triggered segment optimization for '%s' (indexing_threshold=0)",
        collection_name,
    )

    # Wait for optimization to complete by polling collection info
    for _ in range(60):  # max 60 seconds
        info = await client.get_collection(collection_name)
        if info.status == "green" and info.optimizer_status == "ok":
            break
        await asyncio.sleep(1)
    else:
        logger.warning(
            "Optimization of '%s' did not complete within 60s",
            collection_name,
        )

    # Restore original indexing_threshold
    # Note: vacuum_min_vector_number stays at its default (100)
    await client.update_collection(
        collection_name=collection_name,
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=indexing_threshold,
        ),
    )
    logger.info(
        "Restored indexing_threshold=%d for '%s'",
        indexing_threshold,
        collection_name,
    )
