"""Document admin helpers — constants, validators, and utility functions."""

from __future__ import annotations

import io
import math
import re
import zipfile
from pathlib import Path

from cafetera_admin.api.schemas import DocumentResponse, DocumentTableContext
from cafetera_core.storage.models import DocumentRecord

_COOKIE_NAME = "admin_session"
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = {".docx", ".pdf", ".xlsx"}
_ALLOWED_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/pdf",  # .pdf
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/octet-stream",  # browsers sometimes send this
}

_EXT_TO_MIME = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _validate_docx_bytes(data: bytes) -> bool:
    """Validate that bytes represent a valid DOCX file by checking for word/document.xml."""
    try:
        with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
            return 'word/document.xml' in zf.namelist()
    except zipfile.BadZipFile:
        return False


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
    return DocumentResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        title=doc.title,
        s3_key=doc.s3_key,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        size_human=_human_size(doc.size_bytes),
        status=doc.status.value,
        is_search_enabled=doc.is_search_enabled,
        error=doc.error,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
        indexed_at=doc.indexed_at.isoformat() if doc.indexed_at else None,
        chunk_count=doc.chunk_count,
    ).model_dump()


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
) -> DocumentTableContext:
    """Build template context dict for document table partials."""
    pages = math.ceil(total / per_page) if per_page > 0 else 0
    return DocumentTableContext(
        documents=documents,
        human_size=_human_size,
        page=page,
        per_page=per_page,
        pages=pages,
        total=total,
        search=search,
        date_from=date_from,
        date_to=date_to,
        status_filter=status or "",
        source_type_filter=source_type or "",
        sort_field=sort_field or "",
        sort_dir=sort_dir or "",
    )
