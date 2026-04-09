"""Qdrant chunk indexing and management operations.

Provides per-document operations: index, delete, toggle search, count.
Used by ``DocumentService`` in the domain layer and by ``scripts/ingest.py``.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from qdrant_client import models

if TYPE_CHECKING:
    from langchain_core.documents import Document as LCDocument
    from langchain_core.embeddings import Embeddings
    from qdrant_client import QdrantClient

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


def index_chunks(
    client: QdrantClient,
    embeddings: Embeddings,
    collection_name: str,
    chunks: list[LCDocument],
    sparse_embedding=None,
) -> int:
    """Add pre-prepared chunks to the Qdrant collection.

    The collection must already exist.  Returns the number of indexed chunks.
    """
    from langchain_qdrant import QdrantVectorStore

    if not chunks:
        return 0

    kwargs = dict(client=client, collection_name=collection_name, embedding=embeddings)
    if sparse_embedding is not None:
        kwargs["sparse_embedding"] = sparse_embedding
    vs = QdrantVectorStore(**kwargs)
    vs.add_documents(chunks)
    logger.info("Indexed %d chunk(s) in '%s'", len(chunks), collection_name)
    return len(chunks)


def delete_document_chunks(
    client: QdrantClient,
    collection_name: str,
    document_id: str,
) -> None:
    """Delete all vector chunks belonging to the given document."""
    client.delete(
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


def set_search_enabled(
    client: QdrantClient,
    collection_name: str,
    document_id: str,
    *,
    enabled: bool,
) -> None:
    """Update ``is_search_enabled`` on all chunks of a document.

    Uses Qdrant dot-notation payload update so other metadata fields
    are not affected.
    """
    client.set_payload(
        collection_name=collection_name,
        payload={"metadata.is_search_enabled": enabled},
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


def count_document_chunks(
    client: QdrantClient,
    collection_name: str,
    document_id: str,
) -> int:
    """Return the number of chunks belonging to a document in Qdrant."""
    result = client.count(
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
