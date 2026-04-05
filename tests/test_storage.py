"""Tests for app.storage — document metadata model, database init, and CRUD."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.storage.database import init_db
from app.storage.document_repo import DocumentRepository
from app.storage.models import DocumentRecord, DocumentStatus

# ── helpers ───────────────────────────────────────────────────────


def _make_record(**overrides) -> DocumentRecord:
    """Build a ``DocumentRecord`` with sensible defaults.  Override any field."""
    now = datetime.now(UTC)
    defaults = {
        "document_id": uuid.uuid4().hex,
        "filename": "test.docx",
        "title": "Test document",
        "s3_key": "documents/test.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size_bytes": 12345,
        "status": DocumentStatus.pending,
        "is_search_enabled": True,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "indexed_at": None,
        "chunk_count": 0,
    }
    defaults.update(overrides)
    return DocumentRecord(**defaults)


@pytest.fixture()
async def repo(tmp_path):
    """Create a fresh SQLite DB in a temp directory and return a repository."""
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return DocumentRepository(db_path)


# ── Model tests ──────────────────────────────────────────────────


class TestDocumentRecord:
    def test_default_status_is_pending(self):
        rec = _make_record()
        assert rec.status == DocumentStatus.pending

    def test_default_search_enabled(self):
        rec = _make_record()
        assert rec.is_search_enabled is True

    def test_default_chunk_count_zero(self):
        rec = _make_record()
        assert rec.chunk_count == 0

    def test_status_enum_values(self):
        assert DocumentStatus.pending.value == "pending"
        assert DocumentStatus.processing.value == "processing"
        assert DocumentStatus.completed.value == "completed"
        assert DocumentStatus.failed.value == "failed"


# ── Database init ────────────────────────────────────────────────


class TestInitDb:
    async def test_creates_database_file(self, tmp_path):
        db_path = str(tmp_path / "subdir" / "test.db")
        await init_db(db_path)
        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'"
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "documents"

    async def test_idempotent(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        await init_db(db_path)
        await init_db(db_path)  # should not raise


# ── CRUD: create ─────────────────────────────────────────────────


class TestCreate:
    async def test_create_and_get(self, repo):
        rec = _make_record()
        created = await repo.create(rec)
        assert created.document_id == rec.document_id
        assert created.filename == "test.docx"

        fetched = await repo.get(rec.document_id)
        assert fetched is not None
        assert fetched.document_id == rec.document_id
        assert fetched.filename == "test.docx"

    async def test_create_sets_timestamps(self, repo):
        rec = _make_record()
        created = await repo.create(rec)
        assert created.created_at is not None
        assert created.updated_at is not None

    async def test_create_preserves_all_fields(self, repo):
        now = datetime.now(UTC)
        rec = _make_record(
            status=DocumentStatus.completed,
            is_search_enabled=False,
            error="some error",
            indexed_at=now,
            chunk_count=42,
        )
        created = await repo.create(rec)
        fetched = await repo.get(created.document_id)
        assert fetched is not None
        assert fetched.status == DocumentStatus.completed
        assert fetched.is_search_enabled is False
        assert fetched.error == "some error"
        assert fetched.indexed_at is not None
        assert fetched.chunk_count == 42


# ── CRUD: read ───────────────────────────────────────────────────


class TestRead:
    async def test_get_missing_returns_none(self, repo):
        result = await repo.get("nonexistent")
        assert result is None

    async def test_list_all_empty(self, repo):
        result = await repo.list_all()
        assert result == []

    async def test_list_all_returns_newest_first(self, repo):
        r1 = _make_record(document_id="aaa", title="First")
        r2 = _make_record(document_id="bbb", title="Second")
        await repo.create(r1)
        await repo.create(r2)
        docs = await repo.list_all()
        assert len(docs) == 2
        # newest first — r2 was created after r1
        assert docs[0].document_id == "bbb"
        assert docs[1].document_id == "aaa"


# ── CRUD: update ─────────────────────────────────────────────────


class TestUpdate:
    async def test_update_title(self, repo):
        rec = _make_record()
        await repo.create(rec)
        updated = await repo.update(rec.document_id, title="New title")
        assert updated is not None
        assert updated.title == "New title"

    async def test_update_status(self, repo):
        rec = _make_record()
        await repo.create(rec)
        updated = await repo.update(rec.document_id, status=DocumentStatus.processing)
        assert updated is not None
        assert updated.status == DocumentStatus.processing

    async def test_update_error_to_value(self, repo):
        rec = _make_record()
        await repo.create(rec)
        updated = await repo.update(rec.document_id, error="parse failed")
        assert updated is not None
        assert updated.error == "parse failed"

    async def test_update_error_to_none(self, repo):
        rec = _make_record(error="old error")
        await repo.create(rec)
        updated = await repo.update(rec.document_id, error=None)
        assert updated is not None
        assert updated.error is None

    async def test_update_chunk_count_and_indexed_at(self, repo):
        rec = _make_record()
        await repo.create(rec)
        now = datetime.now(UTC)
        updated = await repo.update(rec.document_id, chunk_count=15, indexed_at=now)
        assert updated is not None
        assert updated.chunk_count == 15
        assert updated.indexed_at is not None

    async def test_update_bumps_updated_at(self, repo):
        rec = _make_record()
        created = await repo.create(rec)
        updated = await repo.update(rec.document_id, title="Changed")
        assert updated is not None
        assert updated.updated_at >= created.updated_at

    async def test_update_nonexistent_returns_none(self, repo):
        result = await repo.update("nonexistent", title="x")
        assert result is None

    async def test_update_no_fields_returns_current(self, repo):
        rec = _make_record()
        await repo.create(rec)
        result = await repo.update(rec.document_id)
        assert result is not None
        assert result.document_id == rec.document_id


# ── CRUD: toggle_search ──────────────────────────────────────────


class TestToggleSearch:
    async def test_disable_search(self, repo):
        rec = _make_record(is_search_enabled=True)
        await repo.create(rec)
        toggled = await repo.toggle_search(rec.document_id, enabled=False)
        assert toggled is not None
        assert toggled.is_search_enabled is False

    async def test_enable_search(self, repo):
        rec = _make_record(is_search_enabled=False)
        await repo.create(rec)
        toggled = await repo.toggle_search(rec.document_id, enabled=True)
        assert toggled is not None
        assert toggled.is_search_enabled is True

    async def test_toggle_does_not_change_status(self, repo):
        rec = _make_record(status=DocumentStatus.completed)
        await repo.create(rec)
        toggled = await repo.toggle_search(rec.document_id, enabled=False)
        assert toggled is not None
        assert toggled.status == DocumentStatus.completed

    async def test_toggle_bumps_updated_at(self, repo):
        rec = _make_record()
        created = await repo.create(rec)
        toggled = await repo.toggle_search(rec.document_id, enabled=False)
        assert toggled is not None
        assert toggled.updated_at >= created.updated_at

    async def test_toggle_nonexistent_returns_none(self, repo):
        result = await repo.toggle_search("nonexistent", enabled=False)
        assert result is None


# ── CRUD: delete ─────────────────────────────────────────────────


class TestDelete:
    async def test_delete_existing(self, repo):
        rec = _make_record()
        await repo.create(rec)
        deleted = await repo.delete(rec.document_id)
        assert deleted is True
        assert await repo.get(rec.document_id) is None

    async def test_delete_nonexistent(self, repo):
        deleted = await repo.delete("nonexistent")
        assert deleted is False

    async def test_delete_does_not_affect_others(self, repo):
        r1 = _make_record(document_id="keep")
        r2 = _make_record(document_id="remove")
        await repo.create(r1)
        await repo.create(r2)
        await repo.delete("remove")
        remaining = await repo.list_all()
        assert len(remaining) == 1
        assert remaining[0].document_id == "keep"
