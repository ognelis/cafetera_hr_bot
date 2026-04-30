"""Indexing endpoints — chunk ingestion and deletion."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from qdrant_client import models

from cafetera_rag_service.api.deps import verify_api_key
from cafetera_rag_service.models import (
    IndexChunksRequest,
    IndexChunksResponse,
    InvalidateCacheRequest,
    StatusResponse,
    ToggleSearchRequest,
)
from cafetera_rag_service.rag.retriever import _to_list
from cafetera_rag_service.rag.text_processor import preprocess_russian

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/index", tags=["indexing"], dependencies=[Depends(verify_api_key)])


@router.post("/chunks", response_model=IndexChunksResponse)
async def index_chunks(request: Request, body: IndexChunksRequest) -> IndexChunksResponse:
    """Embed and upsert chunks to Qdrant."""
    res = request.app.state.rag_resources
    if res.qdrant_client is None or res.embeddings is None:
        raise HTTPException(status_code=503, detail="Qdrant or embeddings not available")

    settings = request.app.state.settings

    # Prepare texts and metadata for each chunk
    texts: list[str] = []
    metadatas: list[dict] = []
    for chunk in body.chunks:
        texts.append(chunk.text)
        metadatas.append({
            **chunk.metadata,
            "document_id": body.document_id,
            "filename": body.filename,
            "is_search_enabled": body.is_search_enabled,
        })

    try:
        # Embed all texts
        dense_vectors = await res.embeddings.aembed_documents(texts)

        # Optionally compute sparse vectors
        sparse_vectors: list[models.SparseVector | None] = []
        if res.sparse_embeddings is not None:
            for text in texts:
                processed_text = (
                    preprocess_russian(text) if settings.bm25_lemmatize else text
                )
                sparse_result = res.sparse_embeddings.embed_query(processed_text)
                sparse_vectors.append(
                    models.SparseVector(
                        indices=_to_list(sparse_result.indices),
                        values=_to_list(sparse_result.values),
                    )
                )
        else:
            sparse_vectors = [None] * len(texts)

        # Build PointStruct objects matching QdrantVectorStore payload format
        points: list[models.PointStruct] = []
        for i, text in enumerate(texts):
            vectors: dict = {"dense": dense_vectors[i]}
            if sparse_vectors[i] is not None:
                vectors["bm25"] = sparse_vectors[i]

            payload = {
                "page_content": text,
                "metadata": metadatas[i],
                # Top-level copy for Qdrant filter conditions
                "is_search_enabled": metadatas[i].get("is_search_enabled", True),
            }
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors,
                    payload=payload,
                )
            )

        # Batch upsert
        batch_size = settings.qdrant_upsert_batch_size
        for batch_start in range(0, len(points), batch_size):
            batch = points[batch_start : batch_start + batch_size]
            await res.qdrant_client.upsert(
                collection_name=settings.qdrant_collection,
                points=batch,
            )
    except Exception as exc:
        logger.error(
            "Failed to index %d chunks for document %s: %s",
            len(texts),
            body.document_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Indexing failed") from exc

    logger.info(
        "Indexed %d chunks for document %s",
        len(texts),
        body.document_id,
    )
    return IndexChunksResponse(chunks_indexed=len(texts))


@router.delete("/documents/{document_id}", response_model=StatusResponse)
async def delete_document_chunks(
    document_id: str,
    request: Request,
) -> StatusResponse:
    """Delete all chunks with matching document_id from Qdrant."""
    res = request.app.state.rag_resources
    if res.qdrant_client is None:
        raise HTTPException(status_code=503, detail="Qdrant not available")

    settings = request.app.state.settings
    try:
        await res.qdrant_client.delete(
            collection_name=settings.qdrant_collection,
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
    except Exception as exc:
        logger.error(
            "Failed to delete chunks for document %s: %s",
            document_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Deletion failed") from exc

    logger.info("Deleted all chunks for document %s", document_id)
    return StatusResponse()


@router.patch("/documents/{document_id}/search", response_model=StatusResponse)
async def toggle_document_search(
    document_id: str,
    request: Request,
    body: ToggleSearchRequest,
) -> StatusResponse:
    """Update is_search_enabled payload for all chunks of a document."""
    res = request.app.state.rag_resources
    if res.qdrant_client is None:
        raise HTTPException(status_code=503, detail="Qdrant not available")

    settings = request.app.state.settings
    try:
        await res.qdrant_client.set_payload(
            collection_name=settings.qdrant_collection,
            payload={
                "is_search_enabled": body.is_search_enabled,
                "metadata.is_search_enabled": body.is_search_enabled,
            },
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
    except Exception as exc:
        logger.error(
            "Failed to toggle search for document %s: %s",
            document_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Toggle search failed") from exc

    # Invalidate QA cache so new retrieval reflects the change
    qa_cache: dict = request.app.state.qa_services
    for qa_service in qa_cache.values():
        qa_service.invalidate_document_chain_cache(document_id)

    logger.info(
        "Toggled search for document %s: is_search_enabled=%s",
        document_id,
        body.is_search_enabled,
    )
    return StatusResponse()


@router.post("/cache/invalidate", response_model=StatusResponse)
async def invalidate_cache(
    request: Request,
    body: InvalidateCacheRequest,
) -> StatusResponse:
    """Clear QAService cached chains.

    If document_id is provided, only that document's chain is removed.
    If document_id is None, the entire cache across all QAService instances
    is cleared.
    """
    qa_cache: dict = request.app.state.qa_services
    for qa_service in qa_cache.values():
        qa_service.invalidate_document_chain_cache(body.document_id)
    logger.info(
        "Invalidated cache for document_id=%s (%d services)",
        body.document_id,
        len(qa_cache),
    )
    return StatusResponse()
