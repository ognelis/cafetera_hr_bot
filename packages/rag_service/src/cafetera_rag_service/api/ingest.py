"""Document ingestion endpoint — S3 download, parse, enrich, embed, index."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from qdrant_client import models

from cafetera_rag_service.api.deps import verify_api_key
from cafetera_rag_service.models import IngestRequest, IngestResponse
from cafetera_rag_service.parser import load_document
from cafetera_rag_service.rag.retriever import _to_list

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/index", tags=["indexing"], dependencies=[Depends(verify_api_key)])


def _enrich_chunks(
    chunks,
    *,
    document_id: str,
    filename: str,
    s3_key: str,
    is_search_enabled: bool,
) -> tuple[list[str], list[dict]]:
    """Enrich parsed chunks with document-level metadata.

    The parser already provides clean metadata (headings, captions,
    page_numbers, content_type, section_path). This function adds
    document-level identifiers for indexing and retrieval.
    """
    texts: list[str] = []
    metadatas: list[dict] = []
    for chunk in chunks:
        meta: dict = {
            **chunk.metadata,
            "document_id": document_id,
            "chunk_id": uuid.uuid4().hex,
            "filename": filename,
            "s3_key": s3_key,
            "is_search_enabled": is_search_enabled,
        }
        texts.append(chunk.page_content)
        metadatas.append(meta)
    return texts, metadatas


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(request: Request, body: IngestRequest) -> IngestResponse:
    """Full document pipeline: S3 download → parse → enrich → embed → Qdrant index."""
    res = request.app.state.rag_resources
    settings = request.app.state.settings

    # Step 1: Validate resources
    if res.qdrant_client is None or res.embeddings is None:
        raise HTTPException(status_code=503, detail="Qdrant or embeddings not available")
    if res.s3_storage is None:
        raise HTTPException(status_code=503, detail="S3 storage not available")

    try:
        # Step 2: Delete existing chunks (idempotent for reindexing)
        await res.qdrant_client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.document_id",
                            match=models.MatchValue(value=body.document_id),
                        )
                    ]
                )
            ),
        )

        # Step 3: Download from S3
        file_data = await res.s3_storage.download(body.s3_key)

        # Step 4: Parse document via Docling in thread pool
        suffix = os.path.splitext(body.filename)[1].lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        try:
            chunks = await asyncio.to_thread(load_document, tmp_path, settings)
        finally:
            os.unlink(tmp_path)

        if not chunks:
            logger.warning("No chunks parsed for document %s", body.document_id)
            return IngestResponse(chunks_indexed=0)

        # Step 5: Enrich chunk metadata
        texts, metadatas = _enrich_chunks(
            chunks,
            document_id=body.document_id,
            filename=body.filename,
            s3_key=body.s3_key,
            is_search_enabled=body.is_search_enabled,
        )

        # Step 6: Embed + index (same logic as index_chunks endpoint)
        dense_vectors = await res.embeddings.aembed_documents(texts)

        sparse_vectors: list[models.SparseVector | None] = []
        if res.sparse_embeddings is not None:
            for text in texts:
                sparse_result = res.sparse_embeddings.embed_query(text)
                sparse_vectors.append(
                    models.SparseVector(
                        indices=_to_list(sparse_result.indices),
                        values=_to_list(sparse_result.values),
                    )
                )
        else:
            sparse_vectors = [None] * len(texts)

        points: list[models.PointStruct] = []
        for i, text in enumerate(texts):
            vectors: dict = {"dense": dense_vectors[i]}
            if sparse_vectors[i] is not None:
                vectors["bm25"] = sparse_vectors[i]

            payload = {
                "page_content": text,
                "metadata": metadatas[i],
                # Top-level copy for Qdrant filter conditions
                "is_search_enabled": body.is_search_enabled,
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

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Ingestion failed for document %s: %s",
            body.document_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Ingestion failed") from exc

    # Step 7: Invalidate QA cache
    qa_cache: dict = request.app.state.qa_services
    for qa_service in qa_cache.values():
        qa_service.invalidate_document_chain_cache(body.document_id)

    logger.info(
        "Ingested document %s (%s): %d chunks indexed",
        body.document_id,
        body.filename,
        len(texts),
    )

    # Step 8: Return response
    return IngestResponse(chunks_indexed=len(texts))
