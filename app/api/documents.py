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

from app.api.deps import (
    AdminDep,
    RepoDep,
    S3Dep,
    ServiceDep,
    SettingsDep,
    TemplatesDep,
)
from app.rag.parser import DOCX_MIME, load_docx
from app.storage.models import DocumentRecord, DocumentStatus
from app.storage.s3 import S3Storage

logger = logging.getLogger(__name__)

router = APIRouter()

_COOKIE_NAME = "admin_session"
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = {".docx"}
_ALLOWED_MIMES = {
    DOCX_MIME,
    "application/octet-stream",  # browsers sometimes send this
}


# ── Helpers ───────────────────────────────────────────────────────


def _sanitize_filename(name: str) -> str:
    """Sanitize a user-provided filename to prevent path traversal."""
    name = Path(name).name  # strip directories
    name = re.sub(r"[^\w\s.\-]", "_", name)
    return name or "document.docx"


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


async def _index_in_background(
    service, s3: S3Storage, document_id: str, s3_key: str
) -> None:
    """Download from S3, parse, and index a document.  Runs as a background task."""
    try:
        data = await s3.download(s3_key)
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        try:
            chunks = await asyncio.to_thread(load_docx, tmp_path)
            await service.index_document(document_id, chunks)
            logger.info("Background indexing completed for %s", document_id)
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception:
        logger.error(
            "Background indexing failed for %s", document_id, exc_info=True
        )


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
):
    # Parse date strings to datetime objects
    from datetime import datetime
    dt_from = None
    dt_to = None
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
        except ValueError:
            pass

    documents, total = await repo.list_page(
        page=page, per_page=per_page, search=search,
        date_from=dt_from, date_to=dt_to
    )
    pages = math.ceil(total / per_page) if per_page > 0 else 0
    return templates.TemplateResponse(
        request,
        "documents.html",
        {
            "documents": documents,
            "human_size": _human_size,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "total": total,
            "search": search,
            "date_from": date_from,
            "date_to": date_to,
        },
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
):
    # Parse date strings to datetime objects
    from datetime import datetime
    dt_from = None
    dt_to = None
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
        except ValueError:
            pass

    documents, total = await repo.list_page(
        page=page, per_page=per_page, search=search,
        date_from=dt_from, date_to=dt_to
    )
    pages = math.ceil(total / per_page) if per_page > 0 else 0
    return templates.TemplateResponse(
        request,
        "partials/document_table.html",
        {
            "documents": documents,
            "human_size": _human_size,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "total": total,
            "search": search,
            "date_from": date_from,
            "date_to": date_to,
        },
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


# ── Upload ────────────────────────────────────────────────────────


@router.post("/api/documents/upload")
async def upload_documents(
    request: Request,
    _auth: AdminDep,
    s3: S3Dep,
    service: ServiceDep,
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
):
    """Upload one or more .docx files to S3.  Returns list of created documents."""
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
            errors.append({
                "filename": safe_name,
                "error": f"Unsupported file type: {ext}. Only .docx allowed.",
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

        # Upload to S3
        await s3.upload(s3_key, content, content_type=DOCX_MIME)

        # Create metadata record
        record = await service.create_document(
            filename=stored_name,
            title=Path(safe_name).stem,
            s3_key=s3_key,
            mime_type=DOCX_MIME,
            size_bytes=len(content),
        )

        # Schedule background indexing
        background_tasks.add_task(
            _index_in_background, service, s3, record.document_id, s3_key
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
):
    # Parse date strings to datetime objects
    from datetime import datetime
    dt_from = None
    dt_to = None
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
        except ValueError:
            pass

    docs, total = await repo.list_page(
        page=page, per_page=per_page, search=search,
        date_from=dt_from, date_to=dt_to
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
    }


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
    enabled: Annotated[bool, Form()],
):
    record = await service.toggle_search(document_id, enabled=enabled)
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

    background_tasks.add_task(
        _reindex_in_background, service, s3, document_id, record.s3_key
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


async def _reindex_in_background(
    service, s3: S3Storage, document_id: str, s3_key: str
):
    try:
        data = await s3.download(s3_key)
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        try:
            chunks = await asyncio.to_thread(load_docx, tmp_path)
            await service.reindex_document(document_id, chunks)
            logger.info("Background reindex completed for %s", document_id)
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception:
        logger.error(
            "Background reindex failed for %s", document_id, exc_info=True
        )


@router.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    _auth: AdminDep,
    s3: S3Dep,
    service: ServiceDep,
    repo: RepoDep,
):
    record = await repo.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")

    deleted = await service.delete_document(
        document_id, file_deleter=s3.delete
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

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
    return Response(
        content=data,
        media_type=record.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{record.filename}"',
        },
    )
