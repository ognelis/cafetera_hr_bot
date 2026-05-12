"""CRUD operations for category files in PostgreSQL."""

from __future__ import annotations

import dataclasses
import logging
from datetime import UTC, datetime

from databases import Database
from databases.interfaces import Record

from cafetera_core.storage.category_models import CategoryFileRecord

logger = logging.getLogger(__name__)

_COLUMNS = (
    "id",
    "file_id",
    "category",
    "subcategory",
    "entity_id",
    "filename",
    "s3_key",
    "mime_type",
    "size_bytes",
    "created_at",
    "updated_at",
)


def _row_to_record(row: Record) -> CategoryFileRecord:
    """Convert a database row to a ``CategoryFileRecord``."""
    return CategoryFileRecord(
        id=row["id"],
        file_id=row["file_id"],
        category=row["category"],
        subcategory=row["subcategory"],
        entity_id=row["entity_id"],
        filename=row["filename"],
        s3_key=row["s3_key"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class CategoryFileRepository:
    """Async CRUD repository for category files stored in PostgreSQL."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def upsert(self, record: CategoryFileRecord) -> CategoryFileRecord:
        """Insert or replace file for a category+subcategory+entity slot."""
        now = datetime.now(UTC)
        # If record is new, set timestamps; otherwise update updated_at
        if record.id is None:
            record = dataclasses.replace(record, created_at=now, updated_at=now)
        else:
            record = dataclasses.replace(record, updated_at=now)

        row_id = await self._db.execute(
            query="""
                INSERT INTO category_files
                    (file_id, category, subcategory, entity_id, filename,
                     s3_key, mime_type, size_bytes, created_at, updated_at)
                VALUES (:file_id, :category, :subcategory, :entity_id, :filename,
                        :s3_key, :mime_type, :size_bytes, :created_at, :updated_at)
                ON CONFLICT (category, subcategory, entity_id)
                DO UPDATE SET
                    file_id = EXCLUDED.file_id,
                    filename = EXCLUDED.filename,
                    s3_key = EXCLUDED.s3_key,
                    mime_type = EXCLUDED.mime_type,
                    size_bytes = EXCLUDED.size_bytes,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """,
            values={
                "file_id": record.file_id,
                "category": record.category,
                "subcategory": record.subcategory,
                "entity_id": record.entity_id,
                "filename": record.filename,
                "s3_key": record.s3_key,
                "mime_type": record.mime_type,
                "size_bytes": record.size_bytes,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        )
        if record.id is None:
            record = dataclasses.replace(record, id=row_id)
        return record

    async def get(self, file_id: str) -> CategoryFileRecord | None:
        """Fetch by UUID."""
        cols = ", ".join(_COLUMNS)
        row = await self._db.fetch_one(
            query=f"SELECT {cols} FROM category_files WHERE file_id = :file_id",  # noqa: S608
            values={"file_id": file_id},
        )
        if row is None:
            return None
        return _row_to_record(row)

    async def get_by_slot(
        self, category: str, subcategory: str, entity_id: int
    ) -> CategoryFileRecord | None:
        """Fetch the file for a specific slot+entity."""
        cols = ", ".join(_COLUMNS)
        row = await self._db.fetch_one(
            query=(
                f"SELECT {cols} FROM category_files "  # noqa: S608
                "WHERE category = :category AND subcategory = :subcategory "
                "AND entity_id = :entity_id"
            ),
            values={"category": category, "subcategory": subcategory, "entity_id": entity_id},
        )
        if row is None:
            return None
        return _row_to_record(row)

    async def list_all(self) -> list[CategoryFileRecord]:
        """Return all category files."""
        cols = ", ".join(_COLUMNS)
        rows = await self._db.fetch_all(
            query=f"SELECT {cols} FROM category_files ORDER BY id DESC"  # noqa: S608
        )
        return [_row_to_record(r) for r in rows]

    async def delete(self, file_id: str) -> bool:
        """Remove record by file_id. Returns True if a row was removed."""
        row = await self._db.fetch_one(
            query="DELETE FROM category_files WHERE file_id = :file_id RETURNING id",
            values={"file_id": file_id},
        )
        return row is not None
