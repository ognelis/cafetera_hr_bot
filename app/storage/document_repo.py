"""CRUD operations for document metadata in SQLite."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import aiosqlite

from app.storage.models import DocumentRecord, DocumentStatus

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
)


def _row_to_record(row: aiosqlite.Row) -> DocumentRecord:
    """Convert a database row to a ``DocumentRecord``."""
    return DocumentRecord(
        id=row[0],
        document_id=row[1],
        filename=row[2],
        title=row[3],
        s3_key=row[4],
        mime_type=row[5],
        size_bytes=row[6],
        status=DocumentStatus(row[7]),
        is_search_enabled=bool(row[8]),
        error=row[9],
        created_at=datetime.fromisoformat(row[10]),
        updated_at=datetime.fromisoformat(row[11]),
        indexed_at=datetime.fromisoformat(row[12]) if row[12] else None,
        chunk_count=row[13],
    )


# Sentinel for distinguishing "not passed" from explicit ``None``.
class _SentinelType:
    """Marker for unset optional arguments."""

    def __repr__(self) -> str:
        return "<UNSET>"


_SENTINEL = _SentinelType()


class DocumentRepository:
    """Async CRUD repository for document metadata stored in SQLite."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    # ── Create ────────────────────────────────────────────────────

    async def create(self, record: DocumentRecord) -> DocumentRecord:
        """Insert a new document record and return it."""
        now = datetime.now(UTC)
        record = record.model_copy(update={"created_at": now, "updated_at": now})
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO documents
                    (document_id, filename, title, s3_key, mime_type,
                     size_bytes, status, is_search_enabled, error,
                     created_at, updated_at, indexed_at, chunk_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.document_id,
                    record.filename,
                    record.title,
                    record.s3_key,
                    record.mime_type,
                    record.size_bytes,
                    record.status.value,
                    int(record.is_search_enabled),
                    record.error,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    record.indexed_at.isoformat() if record.indexed_at else None,
                    record.chunk_count,
                ),
            )
            await db.commit()
            # Get the auto-generated id
            record = record.model_copy(update={"id": cursor.lastrowid})
        return record

    # ── Read ──────────────────────────────────────────────────────

    async def get(self, document_id: str) -> DocumentRecord | None:
        """Return a single document by id, or ``None`` if not found."""
        cols = ", ".join(_COLUMNS)
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                f"SELECT {cols} FROM documents WHERE document_id = ?",  # noqa: S608
                (document_id,),
            )
            row = await cursor.fetchone()
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
        params: list[object] = []

        if search:
            search_pattern = f"%{search}%"
            where_clauses.append("(LOWER(title) LIKE LOWER(?) OR LOWER(filename) LIKE LOWER(?))")
            params.extend([search_pattern, search_pattern])

        if date_from is not None:
            where_clauses.append("created_at >= ?")
            params.append(date_from.isoformat())

        if date_to is not None:
            # Set time to end of day for inclusive filtering
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            where_clauses.append("created_at <= ?")
            params.append(date_to_end.isoformat())

        if status and status != "all":
            where_clauses.append("status = ?")
            params.append(status)

        if source_type and source_type != "all":
            if source_type == "docx":
                where_clauses.append("LOWER(filename) LIKE '%.docx'")
            elif source_type == "doc":
                where_clauses.append(
                    "(LOWER(filename) LIKE '%.doc'"
                    " AND LOWER(filename) NOT LIKE '%.docx')"
                )
            elif source_type == "other":
                where_clauses.append(
                    "LOWER(filename) NOT LIKE '%.doc'"
                    " AND LOWER(filename) NOT LIKE '%.docx'"
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
        order_expr = allowed_sort_fields.get(sort_field, "id")
        direction = "ASC" if sort_dir == "asc" else "DESC"
        order_clause = f"ORDER BY {order_expr} {direction}"

        async with aiosqlite.connect(self._db_path) as db:
            # Count total
            count_sql = f"SELECT COUNT(*) FROM documents {where_sql}"  # noqa: S608
            cursor = await db.execute(count_sql, params)
            row = await cursor.fetchone()
            total = row[0] if row else 0

            # Select page
            offset = (page - 1) * per_page
            select_sql = (
                f"SELECT {cols} FROM documents {where_sql} "  # noqa: S608
                f"{order_clause} LIMIT ? OFFSET ?"
            )
            cursor = await db.execute(select_sql, params + [per_page, offset])
            rows = await cursor.fetchall()

        return [_row_to_record(r) for r in rows], total

    # ── Update ────────────────────────────────────────────────────

    async def update(
        self,
        document_id: str,
        *,
        title: str | None = None,
        status: DocumentStatus | None = None,
        error: str | None | _SentinelType = _SENTINEL,
        chunk_count: int | None = None,
        indexed_at: datetime | None | _SentinelType = _SENTINEL,
    ) -> DocumentRecord | None:
        """Update selected fields of a document.  Returns the updated record."""
        sets: list[str] = []
        params: list[object] = []

        if title is not None:
            sets.append("title = ?")
            params.append(title)
        if status is not None:
            sets.append("status = ?")
            params.append(status.value)
        if not isinstance(error, _SentinelType):
            sets.append("error = ?")
            params.append(error)
        if chunk_count is not None:
            sets.append("chunk_count = ?")
            params.append(chunk_count)
        if not isinstance(indexed_at, _SentinelType):
            sets.append("indexed_at = ?")
            params.append(indexed_at.isoformat() if indexed_at else None)

        if not sets:
            return await self.get(document_id)

        sets.append("updated_at = ?")
        params.append(datetime.now(UTC).isoformat())
        params.append(document_id)

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                f"UPDATE documents SET {', '.join(sets)} WHERE document_id = ?",  # noqa: S608
                params,
            )
            await db.commit()

        return await self.get(document_id)

    async def toggle_search(
        self, document_id: str, enabled: bool
    ) -> DocumentRecord | None:
        """Toggle the ``is_search_enabled`` flag without changing status."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE documents SET is_search_enabled = ?, updated_at = ? "
                "WHERE document_id = ?",
                (
                    int(enabled),
                    datetime.now(UTC).isoformat(),
                    document_id,
                ),
            )
            await db.commit()
        return await self.get(document_id)

    # ── Delete ────────────────────────────────────────────────────

    async def delete(self, document_id: str) -> bool:
        """Delete a document record.  Returns ``True`` if a row was removed."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,),
            )
            await db.commit()
            return cursor.rowcount > 0
