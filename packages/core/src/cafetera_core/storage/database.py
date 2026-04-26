"""PostgreSQL database initialisation for document metadata."""

from __future__ import annotations

import logging

from databases import Database

logger = logging.getLogger(__name__)

_CREATE_DOCUMENTS_TABLE = """\
CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    document_id     TEXT UNIQUE NOT NULL,
    filename        TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    s3_key          TEXT    NOT NULL,
    mime_type       TEXT    NOT NULL,
    size_bytes      INTEGER NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending',
    is_search_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    error           TEXT,
    created_at      TIMESTAMPTZ    NOT NULL,
    updated_at      TIMESTAMPTZ    NOT NULL,
    indexed_at      TIMESTAMPTZ,
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    indexing_config TEXT
);
"""

_CREATE_CATEGORY_FILES_TABLE = """\
CREATE TABLE IF NOT EXISTS category_files (
    id              SERIAL PRIMARY KEY,
    file_id         TEXT    NOT NULL UNIQUE,
    category        TEXT    NOT NULL,
    subcategory     TEXT    NOT NULL,
    entity_id       INTEGER NOT NULL,
    filename        TEXT    NOT NULL,
    s3_key          TEXT    NOT NULL,
    mime_type       TEXT    NOT NULL,
    size_bytes      INTEGER NOT NULL,
    created_at      TIMESTAMPTZ    NOT NULL,
    updated_at      TIMESTAMPTZ    NOT NULL
);
"""

_CREATE_CATEGORY_FILES_INDEX = """\
CREATE UNIQUE INDEX IF NOT EXISTS uq_cat_sub_entity
    ON category_files(category, subcategory, entity_id);
"""


_ADD_INDEXING_CONFIG_COLUMN = """\
ALTER TABLE documents ADD COLUMN IF NOT EXISTS indexing_config TEXT;
"""


async def init_db(db: Database) -> None:
    """Create the database tables if they do not exist yet."""
    await db.execute(query=_CREATE_DOCUMENTS_TABLE)
    await db.execute(query=_ADD_INDEXING_CONFIG_COLUMN)
    await db.execute(query=_CREATE_CATEGORY_FILES_TABLE)
    await db.execute(query=_CREATE_CATEGORY_FILES_INDEX)
    logger.info("Database tables initialised")
