"""Document admin routes — router composition and core endpoints.

HTML pages:
    GET  /login          — login form
    POST /login          — authenticate and set cookie
    GET  /logout         — clear cookie and redirect
    GET  /documents      — main admin page (table + upload zone)

API endpoints (all require admin cookie):
    POST   /api/documents/upload           — upload one or more files
    GET    /api/documents                  — list all documents (JSON)
    GET    /api/documents/{id}             — document detail (JSON)
    PATCH  /api/documents/{id}/title       — rename title
    PATCH  /api/documents/{id}/search      — toggle search participation
    POST   /api/documents/{id}/reindex     — re-index document
    DELETE /api/documents/{id}             — full delete

HTMX partials (require admin cookie):
    GET  /partials/document-table          — table body partial
    GET  /partials/document-row/{id}       — single row partial
    GET  /partials/document-status/{id}    — status badge partial (for polling)
"""

from __future__ import annotations

import logging
import math
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse, Response

from app.api.deps import (
    AdminDep,
    IndexingSemaphoreDep,
    QAServiceDep,
    RepoDep,
    S3Dep,
    ServiceDep,
    TemplatesDep,
    parse_date_range,
)

# Sub-routers
from app.api.documents_auth import router as _auth_router
from app.api.documents_bulk import router as _bulk_router

# Helpers re-exported so the module stays a drop-in for any direct imports
from app.api.documents_helpers import (  # noqa: F401
    _ALLOWED_EXTENSIONS,
    _ALLOWED_MIMES,
    _COOKIE_NAME,
    _EXT_TO_MIME,
    _MAX_FILE_SIZE,
    _doc_to_dict,
    _document_table_context,
    _get_mime_from_ext,
    _human_size,
    _sanitize_filename,
    _validate_docx_bytes,
)
from app.api.documents_qa import router as _qa_router
from app.api.documents_upload import _index_document_from_s3  # noqa: F401
from app.api.documents_upload import router as _upload_router
from app.config import Settings

# Re-export for test-patch compatibility  (tests patch these names on this module)
from app.rag.parser import load_document  # noqa: F401
from app.storage.models import DocumentStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Include sub-routers — order matters for path matching
router.include_router(_auth_router)
router.include_router(_upload_router)
router.include_router(_bulk_router)
router.include_router(_qa_router)


# ── Documents HTML page ───────────────────────────────────────────


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(
    request: Request,
    _auth: AdminDep,
    templates: TemplatesDep,
    repo: RepoDep,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    sort_field: str | None = None,
    sort_dir: str | None = None,
):
    dt_from, dt_to = parse_date_range(date_from, date_to)

    documents, total = await repo.list_page(
        page=page, per_page=per_page, search=search,
        date_from=dt_from, date_to=dt_to,
        status=status or None,
        source_type=source_type or None,
        sort_field=sort_field or None,
        sort_dir=sort_dir or None,
    )
    return templates.TemplateResponse(
        request,
        "documents.html",
        dict(_document_table_context(
            documents=documents,
            total=total,
            page=page,
            per_page=per_page,
            search=search,
            date_from=date_from,
            date_to=date_to,
            status=status,
            source_type=source_type,
            sort_field=sort_field,
            sort_dir=sort_dir,
        )),
    )


# ── HTMX partials ────────────────────────────────────────────────


@router.get("/partials/document-table", response_class=HTMLResponse)
async def document_table_partial(
    request: Request,
    _auth: AdminDep,
    templates: TemplatesDep,
    repo: RepoDep,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    sort_field: str | None = None,
    sort_dir: str | None = None,
):
    dt_from, dt_to = parse_date_range(date_from, date_to)

    documents, total = await repo.list_page(
        page=page, per_page=per_page, search=search,
        date_from=dt_from, date_to=dt_to,
        status=status or None,
        source_type=source_type or None,
        sort_field=sort_field or None,
        sort_dir=sort_dir or None,
    )
    return templates.TemplateResponse(
        request,
        "partials/document_table.html",
        dict(_document_table_context(
            documents=documents,
            total=total,
            page=page,
            per_page=per_page,
            search=search,
            date_from=date_from,
            date_to=date_to,
            status=status,
            source_type=source_type,
            sort_field=sort_field,
            sort_dir=sort_dir,
        )),
    )


@router.get("/partials/document-row/{document_id}", response_class=HTMLResponse)
async def document_row_partial(
    document_id: str,
    request: Request,
    _auth: AdminDep,
    templates: TemplatesDep,
    repo: RepoDep,
):
    doc = await repo.get(document_id)
    if doc is None:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request,
        "partials/document_row.html",
        {
            "doc": doc,
            "human_size": _human_size,
        },
    )


@router.get(
    "/partials/document-status/{document_id}", response_class=HTMLResponse
)
async def document_status_partial(
    document_id: str,
    request: Request,
    _auth: AdminDep,
    templates: TemplatesDep,
    repo: RepoDep,
):
    doc = await repo.get(document_id)
    if doc is None:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request,
        "partials/document_row.html",
        {
            "doc": doc,
            "human_size": _human_size,
        },
    )


@router.get("/partials/documents-status", response_class=HTMLResponse)
async def documents_status_partial(
    request: Request,
    _auth: AdminDep,
    templates: TemplatesDep,
    service: ServiceDep,
):
    """Return OOB-swapped rows for all pending/processing documents + poller div.

    This batch endpoint replaces per-row polling to avoid N concurrent requests.
    """
    active_docs, all_docs_to_render = (
        await service.get_active_and_recent_documents()
    )

    # Render OOB rows for each document
    row_html_parts = []
    for doc in all_docs_to_render:
        row_response = templates.TemplateResponse(
            request,
            "partials/document_row.html",
            {
                "doc": doc,
                "human_size": _human_size,
            },
        )
        # Extract the HTML content from the response
        row_body = row_response.body
        row_bytes = bytes(row_body) if isinstance(row_body, memoryview) else row_body
        row_html = row_bytes.decode("utf-8")
        # Add hx-swap-oob="true" attribute to the tr element
        # The row already has id="row-{document_id}" from the template
        row_html = row_html.replace(
            f'id="row-{doc.document_id}"',
            f'id="row-{doc.document_id}" hx-swap-oob="true"'
        )
        row_html_parts.append(row_html)

    # Render the poller div - continues polling if there are active docs
    has_active = len(active_docs) > 0
    poller_response = templates.TemplateResponse(
        request,
        "partials/status_poller.html",
        {"has_active": has_active},
    )
    poller_body = poller_response.body
    poller_bytes = bytes(poller_body) if isinstance(poller_body, memoryview) else poller_body
    poller_html = poller_bytes.decode("utf-8")
    row_html_parts.append(poller_html)

    return HTMLResponse(content="\n".join(row_html_parts))


# ── JSON API ──────────────────────────────────────────────────────


@router.get("/api/documents")
async def list_documents(
    _auth: AdminDep,
    repo: RepoDep,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    sort_field: str | None = None,
    sort_dir: str | None = None,
):
    dt_from, dt_to = parse_date_range(date_from, date_to)

    docs, total = await repo.list_page(
        page=page, per_page=per_page, search=search,
        date_from=dt_from, date_to=dt_to,
        status=status or None,
        source_type=source_type or None,
        sort_field=sort_field or None,
        sort_dir=sort_dir or None,
    )
    return {
        "items": [_doc_to_dict(d) for d in docs],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if per_page > 0 else 0,
        "search": search,
        "date_from": date_from,
        "date_to": date_to,
        "status_filter": status or "",
        "source_type_filter": source_type or "",
        "sort_field": sort_field or "",
        "sort_dir": sort_dir or "",
    }


# ── Single-document endpoints (AFTER bulk routes via sub-router) ──


@router.get("/api/documents/{document_id}")
async def get_document(document_id: str, _auth: AdminDep, repo: RepoDep):
    doc = await repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_dict(doc)


@router.patch("/api/documents/{document_id}/title")
async def update_title(
    document_id: str,
    request: Request,
    _auth: AdminDep,
    service: ServiceDep,
    templates: TemplatesDep,
    repo: RepoDep,
    title: Annotated[str, Form()],
):
    title = title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    record = await service.update_metadata(document_id, title=title)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return templates.TemplateResponse(
            request,
            "partials/document_row.html",
            {"doc": record, "human_size": _human_size},
        )
    return _doc_to_dict(record)


@router.patch("/api/documents/{document_id}/search")
async def toggle_search(
    document_id: str,
    request: Request,
    _auth: AdminDep,
    service: ServiceDep,
    templates: TemplatesDep,
    repo: RepoDep,
    qa: QAServiceDep,
    enabled: Annotated[bool, Form()],
):
    record = await service.toggle_search(document_id, enabled=enabled)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if qa is not None:
        qa.invalidate_document_chain_cache(document_id)

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return templates.TemplateResponse(
            request,
            "partials/document_row.html",
            {"doc": record, "human_size": _human_size},
        )
    return _doc_to_dict(record)


@router.post("/api/documents/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    request: Request,
    _auth: AdminDep,
    s3: S3Dep,
    service: ServiceDep,
    templates: TemplatesDep,
    repo: RepoDep,
    background_tasks: BackgroundTasks,
    semaphore: IndexingSemaphoreDep,
    qa: QAServiceDep,
):
    record = await repo.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify file exists in S3
    if not await s3.exists(record.s3_key):
        raise HTTPException(
            status_code=404, detail="Source file not found in storage"
        )

    # Mark as processing immediately
    await repo.update(document_id, status=DocumentStatus.processing, error=None)

    settings: Settings = request.app.state.settings
    background_tasks.add_task(
        _index_document_from_s3,
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

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        updated = await repo.get(document_id)

        # Render the updated row
        row_response = templates.TemplateResponse(
            request,
            "partials/document_row.html",
            {"doc": updated, "human_size": _human_size},
        )
        row_body = row_response.body
        row_bytes = bytes(row_body) if isinstance(row_body, memoryview) else row_body
        row_html = row_bytes.decode("utf-8")

        # Add hx-swap-oob to the row for proper OOB swap
        row_html = row_html.replace(
            f'id="row-{document_id}"',
            f'id="row-{document_id}" hx-swap-oob="true"'
        )

        # Also include the status poller to ensure polling starts for processing docs
        has_active = await service.has_active_documents()

        poller_response = templates.TemplateResponse(
            request,
            "partials/status_poller.html",
            {"has_active": has_active},
        )
        poller_body = poller_response.body
        poller_bytes = bytes(poller_body) if isinstance(poller_body, memoryview) else poller_body
        poller_html = poller_bytes.decode("utf-8")
        # Add hx-swap-oob to the poller div
        poller_html = poller_html.replace(
            'id="status-poller"',
            'id="status-poller" hx-swap-oob="true"'
        )

        return HTMLResponse(content=row_html + "\n" + poller_html)
    return {"status": "reindexing", "document_id": document_id}


@router.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    _auth: AdminDep,
    s3: S3Dep,
    service: ServiceDep,
    repo: RepoDep,
    qa: QAServiceDep,
):
    record = await repo.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")

    deleted = await service.delete_document(
        document_id, file_deleter=s3.delete
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    if qa is not None:
        qa.invalidate_document_chain_cache(document_id)

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return HTMLResponse("")
    return {"deleted": True, "document_id": document_id}


# ── File download ─────────────────────────────────────────────────


@router.get("/api/documents/{document_id}/download")
async def download_document(
    document_id: str,
    _auth: AdminDep,
    s3: S3Dep,
    repo: RepoDep,
):
    record = await repo.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if not await s3.exists(record.s3_key):
        raise HTTPException(status_code=404, detail="File not found in storage")

    data = await s3.download(record.s3_key)
    # Use RFC 5987 encoding for non-ASCII filenames (e.g. Cyrillic)
    try:
        record.filename.encode("latin-1")
        disposition = f'attachment; filename="{record.filename}"'
    except UnicodeEncodeError:
        from urllib.parse import quote
        ascii_fallback = record.filename.encode("ascii", errors="replace").decode()
        utf8_filename = quote(record.filename)
        disposition = (
            f"attachment; filename=\"{ascii_fallback}\"; "
            f"filename*=UTF-8''{utf8_filename}"
        )
    return Response(
        content=data,
        media_type=record.mime_type,
        headers={"Content-Disposition": disposition},
    )
