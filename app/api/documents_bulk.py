"""Bulk document operations — delete, reindex, toggle search."""

from __future__ import annotations

import asyncio
import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Request,
)
from pydantic import BaseModel

from app.api.deps import (
    AdminDep,
    IndexingSemaphoreDep,
    QAServiceDep,
    RepoDep,
    S3Dep,
    ServiceDep,
    TemplatesDep,
)
from app.api.documents_helpers import _document_table_context
from app.config import Settings
from app.storage.models import DocumentStatus

logger = logging.getLogger(__name__)

router = APIRouter()


class BulkIdsRequest(BaseModel):
    """Request body for bulk operations on document IDs."""

    ids: list[str]


class BulkSearchToggleRequest(BaseModel):
    """Request body for bulk search toggle operation."""

    ids: list[str]
    enabled: bool


@router.post("/api/documents/bulk/delete")
async def bulk_delete_documents(
    request: Request,
    _auth: AdminDep,
    s3: S3Dep,
    service: ServiceDep,
    repo: RepoDep,
    templates: TemplatesDep,
    qa: QAServiceDep,
    body: BulkIdsRequest,
):
    """Delete multiple documents by ID. Returns refreshed document table partial."""
    errors = []

    # Fetch all documents concurrently
    results = await asyncio.gather(
        *[repo.get(document_id) for document_id in body.ids],
        return_exceptions=True,
    )

    for document_id, result in zip(body.ids, results, strict=False):
        if isinstance(result, Exception):
            logger.error("Bulk delete failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {result}")
            continue

        record = result
        if record is None:
            errors.append(f"Document {document_id}: not found")
            continue

        try:
            deleted = await service.delete_document(
                document_id, file_deleter=s3.delete
            )
            if not deleted:
                errors.append(f"Document {document_id}: delete failed")
            else:
                if qa is not None:
                    qa.invalidate_document_chain_cache(document_id)
        except Exception as exc:
            logger.error("Bulk delete failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {exc}")

    # Return refreshed table partial (HTMX pattern)
    documents, total = await repo.list_page(page=1, per_page=10)
    return templates.TemplateResponse(
        request,
        "partials/document_table.html",
        _document_table_context(documents=documents, total=total),
    )


@router.post("/api/documents/bulk/reindex")
async def bulk_reindex_documents(
    request: Request,
    _auth: AdminDep,
    s3: S3Dep,
    service: ServiceDep,
    repo: RepoDep,
    templates: TemplatesDep,
    background_tasks: BackgroundTasks,
    semaphore: IndexingSemaphoreDep,
    qa: QAServiceDep,
    body: BulkIdsRequest,
):
    """Reindex multiple documents by ID. Returns refreshed document table partial."""
    # Lazy import to preserve test-patch compatibility via app.api.documents
    from app.api.documents import (
        _index_document_from_s3 as _bg_index,
    )

    errors = []
    settings: Settings = request.app.state.settings

    # Fetch all documents concurrently
    results = await asyncio.gather(
        *[repo.get(document_id) for document_id in body.ids],
        return_exceptions=True,
    )

    for document_id, result in zip(body.ids, results, strict=False):
        if isinstance(result, Exception):
            logger.error("Bulk reindex failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {result}")
            continue

        record = result
        if record is None:
            errors.append(f"Document {document_id}: not found")
            continue

        try:
            # Verify file exists in S3
            if not await s3.exists(record.s3_key):
                errors.append(f"Document {document_id}: file not found in storage")
                continue

            # Mark as processing immediately
            await repo.update(document_id, status=DocumentStatus.processing, error=None)

            background_tasks.add_task(
                _bg_index,
                service,
                s3,
                document_id,
                record.s3_key,
                semaphore,
                settings.chunk_size,
                settings.chunk_overlap,
                is_reindex=True,
                qa_service=qa,
                strategy=settings.chunk_strategy,
                embeddings=request.app.state.embeddings,
                breakpoint_threshold_type=settings.semantic_breakpoint_threshold_type,
                breakpoint_threshold_amount=settings.semantic_breakpoint_threshold_amount,
            )
        except Exception as exc:
            logger.error("Bulk reindex failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {exc}")

    # Return refreshed table partial (HTMX pattern)
    documents, total = await repo.list_page(page=1, per_page=10)
    return templates.TemplateResponse(
        request,
        "partials/document_table.html",
        _document_table_context(documents=documents, total=total),
    )


@router.patch("/api/documents/bulk/search")
async def bulk_toggle_search(
    request: Request,
    _auth: AdminDep,
    service: ServiceDep,
    repo: RepoDep,
    templates: TemplatesDep,
    qa: QAServiceDep,
    body: BulkSearchToggleRequest,
):
    """Toggle search enabled for multiple documents. Returns refreshed document table partial."""
    errors = []

    # Fetch all documents concurrently
    results = await asyncio.gather(
        *[repo.get(document_id) for document_id in body.ids],
        return_exceptions=True,
    )

    for document_id, result in zip(body.ids, results, strict=False):
        if isinstance(result, Exception):
            logger.error("Bulk toggle search failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {result}")
            continue

        record = result
        if record is None:
            errors.append(f"Document {document_id}: not found")
            continue

        try:
            updated = await service.toggle_search(document_id, enabled=body.enabled)
            if updated is None:
                errors.append(f"Document {document_id}: toggle failed")
            else:
                if qa is not None:
                    qa.invalidate_document_chain_cache(document_id)
        except Exception as exc:
            logger.error("Bulk toggle search failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {exc}")

    # Return refreshed table partial (HTMX pattern)
    documents, total = await repo.list_page(page=1, per_page=10)
    return templates.TemplateResponse(
        request,
        "partials/document_table.html",
        _document_table_context(documents=documents, total=total),
    )
