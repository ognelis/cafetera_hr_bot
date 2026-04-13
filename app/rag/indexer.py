"""Qdrant chunk indexing and management operations.

Provides per-document operations: index, delete, toggle search, count.
Used by ``DocumentService`` in the domain layer and by ``scripts/ingest.py``.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

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
) -> int:
    """Add pre-prepared chunks to the Qdrant collection.

    The collection must already exist.  Returns the number of indexed chunks.
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

    # Build points for upsert (dense + sparse in one point)
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
        vector: dict | list = vectors[i]
        if sparse_vectors is not None:
            sv = sparse_vectors[i]
            vector = {
                "": vectors[i],
                "text-sparse": models.SparseVector(
                    indices=sv.indices,
                    values=sv.values,
                ),
            }
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
