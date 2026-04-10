"""CRUD operations for category files in SQLite."""

from __future__ import annotations

import dataclasses
import logging
from datetime import UTC, datetime

import aiosqlite

from app.storage.category_models import CategoryFileRecord

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


def _row_to_record(row: aiosqlite.Row) -> CategoryFileRecord:
    """Convert a database row to a ``CategoryFileRecord``."""
    return CategoryFileRecord(
        id=row[0],
        file_id=row[1],
        category=row[2],
        subcategory=row[3],
        entity_id=row[4],
        filename=row[5],
        s3_key=row[6],
        mime_type=row[7],
        size_bytes=row[8],
        created_at=datetime.fromisoformat(row[9]),
        updated_at=datetime.fromisoformat(row[10]),
    )


class CategoryFileRepository:
    """Async CRUD repository for category files stored in SQLite."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def upsert(self, record: CategoryFileRecord) -> CategoryFileRecord:
        """Insert or replace file for a category+subcategory+entity slot."""
        now = datetime.now(UTC)
        # If record is new, set timestamps; otherwise update updated_at
        if record.id is None:
            record = dataclasses.replace(record, created_at=now, updated_at=now)
        else:
            record = dataclasses.replace(record, updated_at=now)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT OR REPLACE INTO category_files
                    (file_id, category, subcategory, entity_id, filename,
                     s3_key, mime_type, size_bytes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.file_id,
                    record.category,
                    record.subcategory,
                    record.entity_id,
                    record.filename,
                    record.s3_key,
                    record.mime_type,
                    record.size_bytes,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            await db.commit()
            # If it was an insert, get the auto-generated id
            if record.id is None:
                record = dataclasses.replace(record, id=cursor.lastrowid)
        return record

    async def get(self, file_id: str) -> CategoryFileRecord | None:
        """Fetch by UUID."""
        cols = ", ".join(_COLUMNS)
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                f"SELECT {cols} FROM category_files WHERE file_id = ?",  # noqa: S608
                (file_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_record(row)

    async def get_by_slot(
        self, category: str, subcategory: str, entity_id: int
    ) -> CategoryFileRecord | None:
        """Fetch the file for a specific slot+entity."""
        cols = ", ".join(_COLUMNS)
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                f"SELECT {cols} FROM category_files "  # noqa: S608
                "WHERE category = ? AND subcategory = ? AND entity_id = ?",
                (category, subcategory, entity_id),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_record(row)

    async def list_all(self) -> list[CategoryFileRecord]:
        """Return all category files."""
        cols = ", ".join(_COLUMNS)
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                f"SELECT {cols} FROM category_files ORDER BY id DESC"  # noqa: S608
            )
            rows = await cursor.fetchall()
        return [_row_to_record(r) for r in rows]

    async def delete(self, file_id: str) -> bool:
        """Remove record by file_id. Returns True if a row was removed."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "DELETE FROM category_files WHERE file_id = ?",
                (file_id,),
            )
            await db.commit()
            return cursor.rowcount > 0
