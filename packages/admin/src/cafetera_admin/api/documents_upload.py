"""Document upload endpoint and background indexing task."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Request,
    Response,
    UploadFile,
)

from cafetera_admin.api.deps import (
    AdminDep,
    RAGClientDep,
    S3Dep,
    ServiceDep,
)
from cafetera_admin.api.documents_helpers import (
    _ALLOWED_EXTENSIONS,
    _MAX_FILE_SIZE,
    _doc_to_dict,
    _get_mime_from_ext,
    _human_size,
    _sanitize_filename,
    _validate_docx_bytes,
)
from cafetera_admin.domain.document_service import DocumentService
from cafetera_core.rag_client import RAGClient
from cafetera_core.storage.models import DocumentStatus

logger = logging.getLogger(__name__)

router = APIRouter()


async def _index_document_from_s3(
    document_id: str,
    filename: str,
    s3_key: str,
    *,
    service: DocumentService,
    rag_client: RAGClient,
    semaphore: asyncio.Semaphore,
) -> None:
    """Background task: tell RAG service to ingest the document."""
    async with semaphore:
        try:
            result = await rag_client.ingest_document(
                document_id=document_id,
                filename=filename,
                s3_key=s3_key,
                is_search_enabled=True,
            )
            await service._repo.update(
                document_id,
                status=DocumentStatus.completed,
                chunk_count=result["chunks_indexed"],
                indexed_at=datetime.now(UTC),
                error=None,
                indexing_config={
                    "page_count": result.get("page_count", 0),
                    "binary_hash": result.get("binary_hash", ""),
                    "extracted_title": result.get("extracted_title", ""),
                },
            )
            logger.info(
                "Background indexing completed for %s (%d chunks)",
                document_id,
                result["chunks_indexed"],
            )
        except Exception:
            logger.error(
                "Background indexing failed for %s", document_id, exc_info=True
            )
            await service._repo.update(
                document_id,
                status=DocumentStatus.failed,
                error="Indexing failed",
            )


@router.post("/api/documents/upload")
async def upload_documents(
    request: Request,
    _auth: AdminDep,
    s3: S3Dep,
    service: ServiceDep,
    background_tasks: BackgroundTasks,
    rag_client: RAGClientDep,
    files: list[UploadFile],
):
    """Upload one or more documents (.docx, .pdf) to S3.

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

        # Validate DOCX content for .docx files only (not for .xlsx)
        if ext == ".docx" and not _validate_docx_bytes(content):
            errors.append({
                "filename": safe_name,
                "error": "Invalid or corrupted DOCX file",
            })
            continue

        # Deduplicate S3 key name
        s3_key = await service.generate_unique_s3_key(
            f"documents/{safe_name}", s3,
        )

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
        background_tasks.add_task(
            _index_document_from_s3,
            record.document_id,
            record.filename,
            s3_key,
            service=service,
            rag_client=rag_client,
            semaphore=request.app.state.indexing_semaphore,
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
