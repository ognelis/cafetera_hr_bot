"""Document admin routes — HTML pages and API endpoints.

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

import asyncio
import logging
import math
import re
import secrets
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.api.deps import (
    AdminDep,
    IndexingSemaphoreDep,
    QAServiceDep,
    RepoDep,
    S3Dep,
    ServiceDep,
    SettingsDep,
    TemplatesDep,
    parse_date_range,
)
from app.config import Settings
from app.domain.qa_service import QAService
from app.rag.parser import load_document
from app.storage.models import DocumentRecord, DocumentStatus
from app.storage.s3 import S3Storage

logger = logging.getLogger(__name__)

router = APIRouter()

_COOKIE_NAME = "admin_session"
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = {".docx", ".doc"}
_ALLOWED_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",                                                          # .doc
    "application/octet-stream",  # browsers sometimes send this
}

_EXT_TO_MIME = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
}


# ── Helpers ───────────────────────────────────────────────────────


def _sanitize_filename(name: str) -> str:
    """Sanitize a user-provided filename to prevent path traversal."""
    name = Path(name).name  # strip directories
    name = re.sub(r"[^\w\s.\-]", "_", name)
    return name or "document.docx"


def _get_mime_from_ext(filename: str) -> str | None:
    """Get MIME type from file extension."""
    ext = Path(filename).suffix.lower()
    return _EXT_TO_MIME.get(ext)


def _human_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} TB"


def _doc_to_dict(doc: DocumentRecord) -> dict:
    """Convert a DocumentRecord to a JSON-safe dict."""
    return {
        "document_id": doc.document_id,
        "filename": doc.filename,
        "title": doc.title,
        "s3_key": doc.s3_key,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "size_human": _human_size(doc.size_bytes),
        "status": doc.status.value,
        "is_search_enabled": doc.is_search_enabled,
        "error": doc.error,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
        "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
        "chunk_count": doc.chunk_count,
    }


async def _index_document_from_s3(
    service,
    s3: S3Storage,
    document_id: str,
    s3_key: str,
    semaphore: asyncio.Semaphore,
    chunk_size: int,
    chunk_overlap: int,
    is_reindex: bool = False,
    qa_service: QAService | None = None,
) -> None:
    """Download from S3, parse, and index/reindex a document. Runs as a background task."""
    async with semaphore:
        try:
            data = await s3.download(s3_key)
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(data)
                tmp_path = Path(tmp.name)
            try:
                chunks = await asyncio.to_thread(
                    load_document,
                    tmp_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                if is_reindex:
                    await service.reindex_document(document_id, chunks)
                    logger.info("Background reindex completed for %s", document_id)
                else:
                    await service.index_document(document_id, chunks)
                    logger.info("Background indexing completed for %s", document_id)
            finally:
                await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
        except Exception:
            action = "reindexing" if is_reindex else "indexing"
            logger.error(
                "Background %s failed for %s", action, document_id, exc_info=True
            )
        finally:
            if qa_service is not None:
                qa_service.invalidate_document_chain_cache(document_id)


def _document_table_context(
    documents: list,
    total: int,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    sort_field: str | None = None,
    sort_dir: str | None = None,
) -> dict:
    """Build template context dict for document table partials."""
    pages = math.ceil(total / per_page) if per_page > 0 else 0
    return {
        "documents": documents,
        "human_size": _human_size,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "total": total,
        "search": search,
        "date_from": date_from,
        "date_to": date_to,
        "status_filter": status or "",
        "source_type_filter": source_type or "",
        "sort_field": sort_field or "",
        "sort_dir": sort_dir or "",
    }


# ── Auth pages ────────────────────────────────────────────────────


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    templates: TemplatesDep,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": error},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    settings: SettingsDep,
    api_key: Annotated[str, Form()],
):
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if not secrets.compare_digest(api_key, settings.admin_api_key):
        return RedirectResponse(
            url="/login?error=invalid_key", status_code=303
        )
    response = RedirectResponse(url="/documents", status_code=303)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=settings.admin_api_key,
        httponly=True,
        samesite="strict",
        max_age=60 * 60 * 24,  # 24 hours
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key=_COOKIE_NAME)
    return response


@router.get("/")
async def root_redirect(
    request: Request,
    settings: SettingsDep,
    admin_session: Annotated[str | None, Cookie()] = None,
):
    """Redirect to /documents if authenticated, otherwise to /login."""
    if settings.admin_api_key and admin_session is not None:
        if secrets.compare_digest(admin_session, settings.admin_api_key):
            return RedirectResponse(url="/documents", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


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
        _document_table_context(
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
        ),
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
        _document_table_context(
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
        ),
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
    repo: RepoDep,
):
    """Return OOB-swapped rows for all pending/processing documents + poller div.

    This batch endpoint replaces per-row polling to avoid N concurrent requests.
    """
    # Get all pending and processing documents
    pending_docs, _ = await repo.list_page(
        page=1, per_page=1000, status="pending"
    )
    processing_docs, _ = await repo.list_page(
        page=1, per_page=1000, status="processing"
    )
    active_docs = pending_docs + processing_docs

    # Also get recently finished docs so their final status is pushed to the UI
    recently_finished = await repo.list_recently_finished(seconds=10)

    # Combine: active docs (still polling) + recently finished (final OOB update)
    # Deduplicate by document_id in case of overlap
    seen_ids = {doc.document_id for doc in active_docs}
    all_docs_to_render = active_docs + [
        doc for doc in recently_finished if doc.document_id not in seen_ids
    ]

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
        row_html = row_response.body.decode("utf-8")
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
    poller_html = poller_response.body.decode("utf-8")
    row_html_parts.append(poller_html)

    return HTMLResponse(content="\n".join(row_html_parts))


# ── Upload ────────────────────────────────────────────────────────


@router.post("/api/documents/upload")
async def upload_documents(
    request: Request,
    _auth: AdminDep,
    s3: S3Dep,
    service: ServiceDep,
    background_tasks: BackgroundTasks,
    qa: QAServiceDep,
    files: list[UploadFile],
):
    """Upload one or more documents (.docx, .doc) to S3.

    Returns list of created documents.
    """
    results = []
    errors = []

    for file in files:
        # Validate extension
        if file.filename is None:
            errors.append({"filename": "unknown", "error": "No filename"})
            continue

        safe_name = _sanitize_filename(file.filename)
        ext = Path(safe_name).suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            allowed_list = ", ".join(sorted(_ALLOWED_EXTENSIONS))
            errors.append({
                "filename": safe_name,
                "error": f"Unsupported file type: {ext}. Allowed: {allowed_list}.",
            })
            continue

        # Read content and validate size
        content = await file.read()
        if len(content) > _MAX_FILE_SIZE:
            errors.append({
                "filename": safe_name,
                "error": f"File too large ({_human_size(len(content))}). Max 10 MB.",
            })
            continue

        if len(content) == 0:
            errors.append({
                "filename": safe_name,
                "error": "Empty file",
            })
            continue

        # Deduplicate S3 key name
        s3_key = f"documents/{safe_name}"
        counter = 1
        while await s3.exists(s3_key):
            stem = Path(safe_name).stem
            s3_key = f"documents/{stem}_{counter}{ext}"
            counter += 1

        stored_name = Path(s3_key).name

        # Determine MIME type from extension
        mime_type = _get_mime_from_ext(safe_name) or "application/octet-stream"

        # Upload to S3
        await s3.upload(s3_key, content, content_type=mime_type)

        # Create metadata record
        record = await service.create_document(
            filename=stored_name,
            title=Path(safe_name).stem,
            s3_key=s3_key,
            mime_type=mime_type,
            size_bytes=len(content),
        )

        # Schedule background indexing
        settings: Settings = request.app.state.settings
        background_tasks.add_task(
            _index_document_from_s3,
            service,
            s3,
            record.document_id,
            s3_key,
            request.app.state.indexing_semaphore,
            settings.chunk_size,
            settings.chunk_overlap,
            is_reindex=False,
            qa_service=qa,
        )

        results.append(_doc_to_dict(record))

    # Return JSON for API callers, or trigger HTMX table refresh
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        response = Response(status_code=200)
        response.headers["HX-Trigger"] = "documentsChanged"
        if errors:
            error_msgs = "; ".join(e["error"] for e in errors)
            response.headers["HX-Trigger"] = (
                '{"documentsChanged": null, "showToast": '
                f'{{"message": "Some files failed: {error_msgs}", "type": "error"}}}}'
            )
        return response

    return {"uploaded": results, "errors": errors}


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


# ── Bulk operations (MUST be defined BEFORE any {document_id} routes) ─


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


@router.post("/api/qa/ask-global")
async def ask_global_question(
    _: AdminDep,
    qa: QAServiceDep,
    question: str = Form(...),
):
    """Ask a question across the entire knowledge base. Returns SSE stream."""

    async def event_generator():
        """Generate SSE events with tokens from the LLM."""
        try:
            async for token in qa.stream_ask(question):
                escaped_token = token.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                yield f'data: {{"token": "{escaped_token}"}}\n\n'
            yield 'data: {"done": true}\n\n'
        except Exception as exc:
            logger.error("Error in SSE stream for global question: %s", exc, exc_info=True)
            yield 'data: {"error": "Ошибка при получении ответа"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/api/documents/{document_id}/ask")
async def ask_about_document(
    document_id: str,
    _auth: AdminDep,
    repo: RepoDep,
    qa: QAServiceDep,
    question: Annotated[str, Form()],
):
    """Ask a question about a specific document. Returns SSE stream."""
    doc = await repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if doc.status.value != "completed" or not doc.is_search_enabled:
        raise HTTPException(status_code=400, detail="Документ не готов для вопросов")

    async def event_generator():
        """Generate SSE events with tokens from the LLM."""
        try:
            async for token in qa.stream_about_document(question, document_id):
                # Escape newlines and quotes for JSON serialization
                escaped_token = token.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                yield f'data: {{"token": "{escaped_token}"}}\n\n'
            yield 'data: {"done": true}\n\n'
        except Exception as exc:
            logger.error("Error in SSE stream for document %s: %s", document_id, exc, exc_info=True)
            yield 'data: {"error": "Ошибка при получении ответа"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


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
    )

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        updated = await repo.get(document_id)
        return templates.TemplateResponse(
            request,
            "partials/document_row.html",
            {"doc": updated, "human_size": _human_size},
        )
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
