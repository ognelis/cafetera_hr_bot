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

from cafetera_admin.api.deps import (
    AdminDep,
    IndexingSemaphoreDep,
    RAGClientDep,
    RepoDep,
    S3Dep,
    ServiceDep,
    TemplatesDep,
)
from cafetera_admin.api.documents_helpers import _document_table_context
from cafetera_core.storage.models import DocumentStatus

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
    qa: RAGClientDep,
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
                try:
                    await qa.invalidate_cache(document_id)
                except Exception:
                    pass
        except Exception as exc:
            logger.error("Bulk delete failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {exc}")

    # Return refreshed table partial (HTMX pattern)
    documents, total = await repo.list_page(page=1, per_page=10)
    return templates.TemplateResponse(
        request,
        "partials/document_table.html",
        dict(_document_table_context(documents=documents, total=total)),
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
    qa: RAGClientDep,
    body: BulkIdsRequest,
):
    """Reindex multiple documents by ID. Returns refreshed document table partial."""
    # Lazy import to preserve test-patch compatibility
    from cafetera_admin.api.documents import (
        _index_document_from_s3 as _bg_index,
    )

    errors = []

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

        if isinstance(record, BaseException):
            logger.error("Bulk reindex failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {record}")
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
                document_id,
                record.filename,
                record.s3_key,
                service=service,
                rag_client=qa,
                semaphore=semaphore,
            )
        except Exception as exc:
            logger.error("Bulk reindex failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {exc}")

    # Return refreshed table partial (HTMX pattern)
    documents, total = await repo.list_page(page=1, per_page=10)
    return templates.TemplateResponse(
        request,
        "partials/document_table.html",
        dict(_document_table_context(documents=documents, total=total)),
    )


@router.patch("/api/documents/bulk/search")
async def bulk_toggle_search(
    request: Request,
    _auth: AdminDep,
    service: ServiceDep,
    repo: RepoDep,
    templates: TemplatesDep,
    qa: RAGClientDep,
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
                try:
                    await qa.invalidate_cache(document_id)
                except Exception:
                    pass
        except Exception as exc:
            logger.error("Bulk toggle search failed for %s", document_id, exc_info=True)
            errors.append(f"Document {document_id}: {exc}")

    # Return refreshed table partial (HTMX pattern)
    documents, total = await repo.list_page(page=1, per_page=10)
    return templates.TemplateResponse(
        request,
        "partials/document_table.html",
        dict(_document_table_context(documents=documents, total=total)),
    )



