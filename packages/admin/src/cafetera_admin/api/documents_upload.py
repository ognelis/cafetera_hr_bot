"""Document upload endpoint and background indexing task."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Literal, cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Request,
    Response,
    UploadFile,
)
from langchain_core.embeddings import Embeddings

from cafetera_admin.api.deps import (
    AdminDep,
    QAServiceDep,
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
from cafetera_admin.config import AdminSettings
from cafetera_admin.parser import load_document
from cafetera_core.domain.qa_service import QAService
from cafetera_core.storage.models import DocumentStatus
from cafetera_core.storage.s3 import S3Storage

logger = logging.getLogger(__name__)

router = APIRouter()


async def _download_and_validate(
    s3: S3Storage,
    document_id: str,
    s3_key: str,
    service,
) -> bytes | None:
    """Download a file from S3 and validate DOCX integrity.

    Returns raw bytes on success, or ``None`` if validation fails
    (marking the document as *failed* in the repo).
    """
    data = await s3.download(s3_key)
    ext = Path(s3_key).suffix.lower()

    if ext == ".docx" and not _validate_docx_bytes(data):
        logger.warning(
            "Document %s failed validation: not a valid DOCX file (data size: %d bytes)",
            document_id,
            len(data),
        )
        await service._repo.update(
            document_id,
            status=DocumentStatus.failed,
            error="Invalid or corrupted DOCX file",
        )
        return None
    return data


async def _parse_document_chunks(
    data: bytes,
    s3_key: str,
    document_id: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    strategy: str = "recursive",
    embeddings: Embeddings | None = None,
    breakpoint_threshold_type: str = "percentile",
    breakpoint_threshold_amount: float | int = 95,
) -> list:
    """Write *data* to a temp file, parse it into chunks, and clean up."""
    ext = Path(s3_key).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        tmp_path = Path(tmp.name)
    try:
        chunks = await asyncio.to_thread(
            load_document,
            tmp_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=strategy,
            embeddings=embeddings,
            breakpoint_threshold_type=cast(
                Literal["percentile", "standard_deviation", "interquartile", "gradient"],
                breakpoint_threshold_type,
            ),
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )
    except ValueError as exc:
        if "not a Word file" in str(exc):
            logger.error(
                "Document %s failed to parse: %s (data size: %d bytes)",
                document_id,
                exc,
                len(data),
            )
        raise
    finally:
        await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
    return chunks


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
    strategy: str = "recursive",
    embeddings: Embeddings | None = None,
    breakpoint_threshold_type: str = "percentile",
    breakpoint_threshold_amount: float | int = 95,
) -> None:
    """Download from S3, parse, and index/reindex a document. Runs as a background task."""
    async with semaphore:
        try:
            data = await _download_and_validate(s3, document_id, s3_key, service)
            if data is None:
                return

            chunks = await _parse_document_chunks(
                data,
                s3_key,
                document_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                strategy=strategy,
                embeddings=embeddings,
                breakpoint_threshold_type=breakpoint_threshold_type,
                breakpoint_threshold_amount=breakpoint_threshold_amount,
            )

            if is_reindex:
                await service.reindex_document(document_id, chunks)
                logger.info("Background reindex completed for %s", document_id)
            else:
                await service.index_document(document_id, chunks)
                logger.info("Background indexing completed for %s", document_id)
        except Exception:
            action = "reindexing" if is_reindex else "indexing"
            logger.error(
                "Background %s failed for %s", action, document_id, exc_info=True
            )
        finally:
            if qa_service is not None:
                qa_service.invalidate_document_chain_cache(document_id)


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
        settings: AdminSettings = request.app.state.settings
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
            strategy=settings.chunk_strategy,
            embeddings=request.app.state.embeddings,
            breakpoint_threshold_type=settings.semantic_breakpoint_threshold_type,
            breakpoint_threshold_amount=settings.semantic_breakpoint_threshold_amount,
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
