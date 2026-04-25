"""Category files admin routes — HTML pages and API endpoints for VK bot templates.

HTML pages:
    GET  /category-files      — main admin page (category slots table)

API endpoints (all require admin cookie):
    GET    /api/category-files/slots              — list category slots and entities
    GET    /api/category-files                    — list all uploaded files
    POST   /api/category-files/upload             — upload file for a slot
    GET    /api/category-files/{file_id}/download — download a file
    DELETE /api/category-files/{file_id}          — delete a file

HTMX partials (require admin cookie):
    GET  /partials/category-slot/{category}/{subcategory}/{entity_id} — single slot cell
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, Response

from cafetera_admin.api.deps import (
    AdminDep,
    CategoryFileServiceDep,
    TemplatesDep,
)
from cafetera_admin.api.schemas import CategoryFileResponse, CategoryListResponse, EntityInfo
from cafetera_core.storage.category_models import (
    CATEGORY_SLOTS,
    LEGAL_ENTITIES,
    is_valid_slot,
)

router = APIRouter()

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


def _file_to_dict(file_record) -> dict:
    """Convert a CategoryFileRecord to a JSON-safe dict."""
    return CategoryFileResponse(
        file_id=file_record.file_id,
        category=file_record.category,
        subcategory=file_record.subcategory,
        entity_id=file_record.entity_id,
        filename=file_record.filename,
        s3_key=file_record.s3_key,
        mime_type=file_record.mime_type,
        size_bytes=file_record.size_bytes,
        size_human=_human_size(file_record.size_bytes),
        created_at=file_record.created_at.isoformat(),
        updated_at=file_record.updated_at.isoformat(),
    ).model_dump()


def _entity_short_name(entity_id: int) -> str:
    """Get short name for entity (first word of company name)."""
    full_name = LEGAL_ENTITIES.get(entity_id, "")
    # Extract "Кафетера" from "ООО «Кафетера Групп Рус»"
    match = re.search(r'«([^»]+)»', full_name)
    if match:
        return match.group(1).split()[0]
    return full_name[:10]


# ── HTML page ─────────────────────────────────────────────────────


@router.get("/category-files", response_class=HTMLResponse)
async def category_files_page(
    request: Request,
    _auth: AdminDep,
    templates: TemplatesDep,
    svc: CategoryFileServiceDep,
):
    """Render the category files admin page."""
    files = await svc.get_all_files()

    # Build a lookup dict: (category, subcategory, entity_id) -> file
    file_lookup = {}
    for f in files:
        key = (f.category, f.subcategory, f.entity_id)
        file_lookup[key] = f

    return templates.TemplateResponse(
        request,
        "category_files.html",
        {
            "category_slots": CATEGORY_SLOTS,
            "legal_entities": LEGAL_ENTITIES,
            "entity_short_name": _entity_short_name,
            "file_lookup": file_lookup,
            "human_size": _human_size,
        },
    )


# ── API endpoints ─────────────────────────────────────────────────


@router.get("/api/category-files/slots")
async def list_slots(
    request: Request,
    _auth: AdminDep,
):
    """Return CATEGORY_SLOTS mapping + entity list for UI rendering."""
    return CategoryListResponse(
        categories=CATEGORY_SLOTS,
        entities=[
            EntityInfo(id=eid, name=name, short_name=_entity_short_name(eid))
            for eid, name in LEGAL_ENTITIES.items()
        ],
    ).model_dump()


@router.get("/api/category-files")
async def list_files(
    request: Request,
    _auth: AdminDep,
    svc: CategoryFileServiceDep,
):
    """List all uploaded category files."""
    files = await svc.get_all_files()
    return {"items": [_file_to_dict(f) for f in files]}


@router.post("/api/category-files/upload")
async def upload_file(
    request: Request,
    category: Annotated[str, Form(...)],
    subcategory: Annotated[str, Form(...)],
    entity_id: Annotated[int, Form(...)],
    file: Annotated[UploadFile, File(...)],
    _auth: AdminDep,
    svc: CategoryFileServiceDep,
    templates: TemplatesDep,
):
    """Upload file for a slot. Returns HTMX partial for the cell."""
    # Validate slot
    if not is_valid_slot(category, subcategory):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category/subcategory: {category}/{subcategory}",
        )

    # Validate entity
    if entity_id not in LEGAL_ENTITIES:
        raise HTTPException(status_code=400, detail=f"Invalid entity_id: {entity_id}")

    # Validate file
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No filename provided")

    safe_name = _sanitize_filename(file.filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(_ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {allowed_list}.",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({_human_size(len(content))}). Max 10 MB.",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Determine MIME type from extension
    mime_type = _get_mime_from_ext(safe_name) or "application/octet-stream"

    # Upload via service
    record = await svc.upload_file(
        category=category,
        subcategory=subcategory,
        entity_id=entity_id,
        filename=safe_name,
        data=content,
        content_type=mime_type,
    )

    # Return HTMX partial for the cell
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return templates.TemplateResponse(
            request,
            "partials/category_slot.html",
            {
                "category": category,
                "subcategory": subcategory,
                "entity_id": entity_id,
                "file": record,
                "human_size": _human_size,
            },
        )

    return _file_to_dict(record)


@router.get("/api/category-files/{file_id}/download")
async def download_file(
    file_id: str,
    request: Request,
    _auth: AdminDep,
    svc: CategoryFileServiceDep,
):
    """Download a category file."""
    try:
        data, filename = await svc.download_file(file_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail="File not found") from err

    # Use RFC 5987 encoding for non-ASCII filenames
    try:
        filename.encode("latin-1")
        disposition = f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        from urllib.parse import quote
        ascii_fallback = filename.encode("ascii", errors="replace").decode()
        utf8_filename = quote(filename)
        disposition = (
            f'attachment; filename="{ascii_fallback}"; '
            f"filename*=UTF-8''{utf8_filename}"
        )

    mime_type = _get_mime_from_ext(filename) or "application/octet-stream"
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": disposition},
    )


@router.delete("/api/category-files/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    _auth: AdminDep,
    svc: CategoryFileServiceDep,
    templates: TemplatesDep,
    category: str | None = None,
    subcategory: str | None = None,
    entity_id: int | None = None,
):
    """Delete a category file. Returns HTMX partial for empty cell."""
    await svc.delete_file(file_id)

    # Return HTMX partial for empty cell
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx and category and subcategory and entity_id is not None:
        return templates.TemplateResponse(
            request,
            "partials/category_slot.html",
            {
                "category": category,
                "subcategory": subcategory,
                "entity_id": entity_id,
                "file": None,
                "human_size": _human_size,
            },
        )

    return {"deleted": True, "file_id": file_id}


# ── HTMX partials ─────────────────────────────────────────────────


@router.get(
    "/partials/category-slot/{category}/{subcategory}/{entity_id}",
    response_class=HTMLResponse,
)
async def category_slot_partial(
    category: str,
    subcategory: str,
    entity_id: int,
    request: Request,
    _auth: AdminDep,
    svc: CategoryFileServiceDep,
    templates: TemplatesDep,
):
    """Return partial HTML for a single slot cell."""
    file_record = await svc.get_file(category, subcategory, entity_id)

    return templates.TemplateResponse(
        request,
        "partials/category_slot.html",
        {
            "category": category,
            "subcategory": subcategory,
            "entity_id": entity_id,
            "file": file_record,
            "human_size": _human_size,
        },
    )
