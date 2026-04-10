"""SQLite database initialisation for document metadata."""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

_CREATE_DOCUMENTS_TABLE = """\
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     TEXT UNIQUE NOT NULL,
    filename        TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    s3_key          TEXT    NOT NULL,
    mime_type       TEXT    NOT NULL,
    size_bytes      INTEGER NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending',
    is_search_enabled INTEGER NOT NULL DEFAULT 1,
    error           TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    indexed_at      TEXT,
    chunk_count     INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_CATEGORY_FILES_TABLE = """\
CREATE TABLE IF NOT EXISTS category_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id         TEXT    NOT NULL UNIQUE,
    category        TEXT    NOT NULL,
    subcategory     TEXT    NOT NULL,
    entity_id       INTEGER NOT NULL,
    filename        TEXT    NOT NULL,
    s3_key          TEXT    NOT NULL,
    mime_type       TEXT    NOT NULL,
    size_bytes      INTEGER NOT NULL,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);
"""

_CREATE_CATEGORY_FILES_INDEX = """\
CREATE UNIQUE INDEX IF NOT EXISTS uq_cat_sub_entity
    ON category_files(category, subcategory, entity_id);
"""


async def init_db(db_path: str) -> None:
    """Create the database file and tables if they do not exist yet."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_CREATE_DOCUMENTS_TABLE)
        await db.execute(_CREATE_CATEGORY_FILES_TABLE)
        await db.execute(_CREATE_CATEGORY_FILES_INDEX)
        await db.commit()
    logger.info("Database initialised at %s", db_path)
