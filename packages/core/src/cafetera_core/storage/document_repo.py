"""CRUD operations for document metadata in PostgreSQL."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from databases import Database
from databases.interfaces import Record

from cafetera_core.storage.models import DocumentRecord, DocumentStatus

logger = logging.getLogger(__name__)

_COLUMNS = (
    "id",
    "document_id",
    "filename",
    "title",
    "s3_key",
    "mime_type",
    "size_bytes",
    "status",
    "is_search_enabled",
    "error",
    "created_at",
    "updated_at",
    "indexed_at",
    "chunk_count",
    "indexing_config",
)


def _row_to_record(row: Record) -> DocumentRecord:
    """Convert a database row to a ``DocumentRecord``."""
    raw_config = row["indexing_config"]
    indexing_config = json.loads(raw_config) if raw_config else None
    return DocumentRecord(
        id=row["id"],
        document_id=row["document_id"],
        filename=row["filename"],
        title=row["title"],
        s3_key=row["s3_key"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        status=DocumentStatus(row["status"]),
        is_search_enabled=bool(row["is_search_enabled"]),
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        indexed_at=row["indexed_at"],
        chunk_count=row["chunk_count"],
        indexing_config=indexing_config,
    )


# Sentinel for distinguishing "not passed" from explicit ``None``.
class _SentinelType:
    """Marker for unset optional arguments."""

    def __repr__(self) -> str:
        return "<UNSET>"


_SENTINEL = _SentinelType()


class DocumentRepository:
    """Async CRUD repository for document metadata stored in PostgreSQL."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ── Create ────────────────────────────────────────────────────

    async def create(self, record: DocumentRecord) -> DocumentRecord:
        """Insert a new document record and return it."""
        now = datetime.now(UTC)
        record = record.model_copy(update={"created_at": now, "updated_at": now})
        row_id = await self._db.execute(
            query="""
                INSERT INTO documents
                    (document_id, filename, title, s3_key, mime_type,
                     size_bytes, status, is_search_enabled, error,
                     created_at, updated_at, indexed_at, chunk_count,
                     indexing_config)
                VALUES (:document_id, :filename, :title, :s3_key, :mime_type,
                        :size_bytes, :status, :is_search_enabled, :error,
                        :created_at, :updated_at, :indexed_at, :chunk_count,
                        :indexing_config)
                RETURNING id
            """,
            values={
                "document_id": record.document_id,
                "filename": record.filename,
                "title": record.title,
                "s3_key": record.s3_key,
                "mime_type": record.mime_type,
                "size_bytes": record.size_bytes,
                "status": record.status.value,
                "is_search_enabled": record.is_search_enabled,
                "error": record.error,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "indexed_at": record.indexed_at,
                "chunk_count": record.chunk_count,
                "indexing_config": (
                    json.dumps(record.indexing_config)
                    if record.indexing_config
                    else None
                ),
            },
        )
        record = record.model_copy(update={"id": row_id})
        return record

    # ── Read ──────────────────────────────────────────────────────

    async def get(self, document_id: str) -> DocumentRecord | None:
        """Return a single document by id, or ``None`` if not found."""
        cols = ", ".join(_COLUMNS)
        row = await self._db.fetch_one(
            query=f"SELECT {cols} FROM documents WHERE document_id = :document_id",  # noqa: S608
            values={"document_id": document_id},
        )
        if row is None:
            return None
        return _row_to_record(row)

    async def list_page(
        self, *, page: int = 1, per_page: int = 20, search: str | None = None,
        date_from: datetime | None = None, date_to: datetime | None = None,
        status: str | None = None,
        source_type: str | None = None,
        sort_field: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[DocumentRecord], int]:
        """Return (documents, total_count) ordered by id DESC with pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            search: Search string for title/filename
            date_from: Filter documents created on or after this date (inclusive)
            date_to: Filter documents created on or before this date (inclusive)
            status: Filter by document status
            source_type: Filter by source type ('docx', 'doc', 'other')
            sort_field: Field to sort by ('title', 'created_at', 'status')
            sort_dir: Sort direction ('asc' or 'desc')
        """
        cols = ", ".join(_COLUMNS)

        # Build WHERE clauses and parameters
        where_clauses: list[str] = []
        params: dict[str, object] = {}

        if search:
            search_pattern = f"%{search}%"
            where_clauses.append("(title ILIKE :search_title OR filename ILIKE :search_filename)")
            params["search_title"] = search_pattern
            params["search_filename"] = search_pattern

        if date_from is not None:
            where_clauses.append("created_at >= :date_from")
            params["date_from"] = date_from

        if date_to is not None:
            # Set time to end of day for inclusive filtering
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            where_clauses.append("created_at <= :date_to")
            params["date_to"] = date_to_end

        if status and status != "all":
            where_clauses.append("status = :status")
            params["status"] = status

        if source_type and source_type != "all":
            if source_type == "docx":
                where_clauses.append("filename ILIKE '%.docx'")
            elif source_type == "doc":
                where_clauses.append(
                    "(filename ILIKE '%.doc'"
                    " AND filename NOT ILIKE '%.docx')"
                )
            elif source_type == "pdf":
                where_clauses.append("filename ILIKE '%.pdf'")
            elif source_type == "xlsx":
                where_clauses.append("filename ILIKE '%.xlsx'")
            elif source_type == "other":
                where_clauses.append(
                    "filename NOT ILIKE '%.doc'"
                    " AND filename NOT ILIKE '%.docx'"
                    " AND filename NOT ILIKE '%.pdf'"
                    " AND filename NOT ILIKE '%.xlsx'"
                )

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # Build ORDER BY clause
        allowed_sort_fields = {
            "title": "LOWER(title)",
            "created_at": "created_at",
            "status": "status",
        }
        order_expr = allowed_sort_fields.get(sort_field or "", "id")
        direction = "ASC" if sort_dir == "asc" else "DESC"
        order_clause = f"ORDER BY {order_expr} {direction}"

        # Count total
        count_sql = f"SELECT COUNT(*) FROM documents {where_sql}"  # noqa: S608
        total = await self._db.fetch_val(query=count_sql, values=params) or 0

        # Select page
        offset = (page - 1) * per_page
        select_sql = (
            f"SELECT {cols} FROM documents {where_sql} "  # noqa: S608
            f"{order_clause} LIMIT :limit OFFSET :offset"
        )
        page_params = {**params, "limit": per_page, "offset": offset}
        rows = await self._db.fetch_all(query=select_sql, values=page_params)

        return [_row_to_record(r) for r in rows], total

    # ── Update ────────────────────────────────────────────────────

    async def update(
        self,
        document_id: str,
        *,
        title: str | None = None,
        status: DocumentStatus | None = None,
        is_search_enabled: bool | _SentinelType = _SENTINEL,
        error: str | None | _SentinelType = _SENTINEL,
        chunk_count: int | None = None,
        indexed_at: datetime | None | _SentinelType = _SENTINEL,
        indexing_config: dict | None | _SentinelType = _SENTINEL,
    ) -> DocumentRecord | None:
        """Update selected fields of a document.  Returns the updated record."""
        sets: list[str] = []
        params: dict[str, object] = {"document_id": document_id}
        param_counter = 0

        def _next_param() -> str:
            nonlocal param_counter
            param_counter += 1
            return f"p{param_counter}"

        if title is not None:
            param = _next_param()
            sets.append(f"title = :{param}")
            params[param] = title
        if status is not None:
            param = _next_param()
            sets.append(f"status = :{param}")
            params[param] = status.value
        if not isinstance(is_search_enabled, _SentinelType):
            param = _next_param()
            sets.append(f"is_search_enabled = :{param}")
            params[param] = is_search_enabled
        if not isinstance(error, _SentinelType):
            param = _next_param()
            sets.append(f"error = :{param}")
            params[param] = error
        if chunk_count is not None:
            param = _next_param()
            sets.append(f"chunk_count = :{param}")
            params[param] = chunk_count
        if not isinstance(indexed_at, _SentinelType):
            param = _next_param()
            sets.append(f"indexed_at = :{param}")
            params[param] = indexed_at
        if not isinstance(indexing_config, _SentinelType):
            param = _next_param()
            sets.append(f"indexing_config = :{param}")
            params[param] = (
                json.dumps(indexing_config) if indexing_config else None
            )

        if not sets:
            return await self.get(document_id)

        param = _next_param()
        sets.append(f"updated_at = :{param}")
        params[param] = datetime.now(UTC)

        await self._db.execute(
            query=f"UPDATE documents SET {', '.join(sets)} WHERE document_id = :document_id",  # noqa: S608
            values=params,
        )

        return await self.get(document_id)

    async def toggle_search(
        self, document_id: str, enabled: bool
    ) -> DocumentRecord | None:
        """Toggle the ``is_search_enabled`` flag without changing status."""
        await self._db.execute(
            query=(
                "UPDATE documents SET is_search_enabled = :enabled, updated_at = :updated_at "
                "WHERE document_id = :document_id"
            ),
            values={
                "enabled": enabled,
                "updated_at": datetime.now(UTC),
                "document_id": document_id,
            },
        )
        return await self.get(document_id)

    # ── Delete ────────────────────────────────────────────────────

    async def list_recently_finished(self, *, seconds: int = 10) -> list[DocumentRecord]:
        """Return documents that completed or failed within the last *seconds*."""
        cols = ", ".join(_COLUMNS)
        cutoff = datetime.now(UTC) - timedelta(seconds=seconds)
        rows = await self._db.fetch_all(
            query=(
                f"SELECT {cols} FROM documents "  # noqa: S608
                "WHERE status IN ('completed', 'failed') AND updated_at >= :cutoff"
            ),
            values={"cutoff": cutoff},
        )
        return [_row_to_record(r) for r in rows]

    async def delete(self, document_id: str) -> bool:
        """Delete a document record.  Returns ``True`` if a row was removed."""
        row = await self._db.fetch_one(
            query="DELETE FROM documents WHERE document_id = :document_id RETURNING id",
            values={"document_id": document_id},
        )
        return row is not None
