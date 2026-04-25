"""Tests for app.domain.category_file_service — category file lifecycle."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from databases import Database

from cafetera_core.domain.category_file_service import CategoryFileService
from cafetera_core.storage.category_models import LEGAL_ENTITIES, CategoryFileRecord
from cafetera_core.storage.category_repo import CategoryFileRepository
from cafetera_core.storage.database import init_db

# ── helpers ───────────────────────────────────────────────────────


def _make_record(**overrides) -> CategoryFileRecord:
    """Build a CategoryFileRecord with sensible defaults."""
    now = datetime.now(UTC)
    defaults = {
        "id": None,
        "file_id": uuid.uuid4().hex,
        "category": "hire",
        "subcategory": "hire_checklist",
        "entity_id": 1,
        "filename": "test.docx",
        "s3_key": "category-files/1/test_file_id.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size_bytes": 12345,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return CategoryFileRecord(**defaults)


@pytest.fixture()
async def repo(pg_container):
    """Create a fresh PostgreSQL DB and return a CategoryFileRepository."""
    raw_url = pg_container.get_connection_url()
    # get_connection_url() returns postgresql+psycopg2://...
    # databases[asyncpg] needs postgresql://...
    url = raw_url.replace("postgresql+psycopg2", "postgresql")
    db = Database(url)
    await db.connect()
    # Clean tables before each test for isolation
    await db.execute(query="DROP TABLE IF EXISTS category_files CASCADE")
    await db.execute(query="DROP TABLE IF EXISTS documents CASCADE")
    await init_db(db)
    yield CategoryFileRepository(db)
    await db.disconnect()


@pytest.fixture()
def mock_s3():
    """Mock S3Storage with async methods."""
    s3 = MagicMock()
    s3.upload = AsyncMock()
    s3.download = AsyncMock(return_value=b"file content here")
    s3.delete = AsyncMock()
    return s3


@pytest.fixture()
def service(repo, mock_s3):
    """Create a CategoryFileService with mocked S3."""
    return CategoryFileService(repo=repo, s3=mock_s3)


# ── upload_file ───────────────────────────────────────────────────


class TestUploadFile:
    async def test_upload_file_creates_record(self, service, repo, mock_s3):
        data = b"file content bytes"
        result = await service.upload_file(
            category="hire",
            subcategory="hire_checklist",
            entity_id=1,
            filename="document.docx",
            data=data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # Verify DB record created
        assert result.category == "hire"
        assert result.subcategory == "hire_checklist"
        assert result.entity_id == 1
        assert result.filename == "document.docx"
        assert result.size_bytes == len(data)
        assert result.mime_type == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert result.file_id is not None
        assert result.id is not None

        # Verify S3 called with right key prefix
        mock_s3.upload.assert_awaited_once()
        call_args = mock_s3.upload.call_args
        s3_key = call_args[0][0]  # first positional arg
        assert s3_key.startswith("category-files/1/")
        assert s3_key.endswith("_document.docx")
        assert call_args[0][1] == data  # second positional arg is data

    async def test_upload_file_replaces_existing(self, service, repo, mock_s3):
        """Upload to same slot twice should delete old S3 key and upload new one."""
        # First upload
        result1 = await service.upload_file(
            category="hire",
            subcategory="hire_checklist",
            entity_id=1,
            filename="old.docx",
            data=b"old content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        old_s3_key = result1.s3_key

        # Second upload to same slot
        _ = await service.upload_file(
            category="hire",
            subcategory="hire_checklist",
            entity_id=1,
            filename="new.docx",
            data=b"new content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # Verify old S3 key was deleted
        mock_s3.delete.assert_awaited_once_with(old_s3_key)

        # Verify new file uploaded
        assert mock_s3.upload.call_count == 2

        # Verify DB has only the new record
        all_files = await repo.list_all()
        assert len(all_files) == 1
        assert all_files[0].filename == "new.docx"

    async def test_upload_file_invalid_slot(self, service, mock_s3):
        with pytest.raises(ValueError, match="Invalid category/subcategory"):
            await service.upload_file(
                category="invalid",
                subcategory="invalid",
                entity_id=1,
                filename="test.docx",
                data=b"content",
                content_type="application/octet-stream",
            )

        # S3 should not be called
        mock_s3.upload.assert_not_awaited()

    async def test_upload_file_invalid_entity(self, service, mock_s3):
        with pytest.raises(ValueError, match="Invalid entity_id"):
            await service.upload_file(
                category="hire",
                subcategory="hire_checklist",
                entity_id=999,
                filename="test.docx",
                data=b"content",
                content_type="application/octet-stream",
            )

        # S3 should not be called
        mock_s3.upload.assert_not_awaited()

    async def test_upload_file_all_valid_entities(self, service, repo, mock_s3):
        """Test that all legal entities are accepted."""
        for entity_id in LEGAL_ENTITIES:
            result = await service.upload_file(
                category="hire",
                subcategory="hire_checklist",
                entity_id=entity_id,
                filename=f"doc{entity_id}.docx",
                data=b"content",
                content_type="application/octet-stream",
            )
            assert result.entity_id == entity_id
            assert f"category-files/{entity_id}/" in result.s3_key

        # Should have 4 files
        all_files = await repo.list_all()
        assert len(all_files) == 4


# ── get_file ──────────────────────────────────────────────────────


class TestGetFile:
    async def test_get_file_delegates_to_repo(self, service, repo):
        # Create a record first
        rec = _make_record(
            category="fire",
            subcategory="fire_resignation",
            entity_id=2,
        )
        await repo.upsert(rec)

        # Get via service
        result = await service.get_file("fire", "fire_resignation", 2)

        assert result is not None
        assert result.file_id == rec.file_id
        assert result.category == "fire"
        assert result.subcategory == "fire_resignation"
        assert result.entity_id == 2

    async def test_get_file_not_found(self, service):
        result = await service.get_file("nonexistent", "slot", 1)
        assert result is None


# ── get_all_files ─────────────────────────────────────────────────


class TestGetAllFiles:
    async def test_get_all_files_delegates_to_repo(self, service, repo):
        # Create multiple records
        rec1 = _make_record(file_id=uuid.uuid4().hex, category="hire")
        rec2 = _make_record(file_id=uuid.uuid4().hex, category="fire")
        await repo.upsert(rec1)
        await repo.upsert(rec2)

        result = await service.get_all_files()

        assert len(result) == 2
        file_ids = {f.file_id for f in result}
        assert file_ids == {rec1.file_id, rec2.file_id}

    async def test_get_all_files_empty(self, service):
        result = await service.get_all_files()
        assert result == []


# ── delete_file ───────────────────────────────────────────────────


class TestDeleteFile:
    async def test_delete_file_calls_s3_and_repo(self, service, repo, mock_s3):
        # Create a record
        rec = _make_record(s3_key="category-files/1/file.docx")
        created = await repo.upsert(rec)

        # Delete via service
        await service.delete_file(created.file_id)

        # Verify S3 delete called
        mock_s3.delete.assert_awaited_once_with("category-files/1/file.docx")

        # Verify DB record deleted
        fetched = await repo.get(created.file_id)
        assert fetched is None

    async def test_delete_file_not_found_no_error(self, service, mock_s3):
        """Deleting a non-existent file_id should not raise an error."""
        await service.delete_file("nonexistent-file-id")

        # S3 should not be called if record doesn't exist
        mock_s3.delete.assert_not_awaited()


# ── download_file ─────────────────────────────────────────────────


class TestDownloadFile:
    async def test_download_file_returns_bytes_and_filename(self, service, repo, mock_s3):
        # Create a record
        rec = _make_record(
            file_id=uuid.uuid4().hex,
            filename="mytemplate.docx",
            s3_key="category-files/1/myfile.docx",
        )
        created = await repo.upsert(rec)

        mock_s3.download.return_value = b"file bytes from s3"

        # Download via service
        data, filename = await service.download_file(created.file_id)

        assert data == b"file bytes from s3"
        assert filename == "mytemplate.docx"
        mock_s3.download.assert_awaited_once_with("category-files/1/myfile.docx")

    async def test_download_file_not_found_raises(self, service, mock_s3):
        with pytest.raises(FileNotFoundError, match="Category file nonexistent not found"):
            await service.download_file("nonexistent")

        # S3 should not be called
        mock_s3.download.assert_not_awaited()

    async def test_download_file_s3_error_propagates(self, service, repo, mock_s3):
        """S3 errors should propagate up."""
        rec = _make_record(s3_key="category-files/1/file.docx")
        created = await repo.upsert(rec)

        mock_s3.download.side_effect = RuntimeError("S3 connection failed")

        with pytest.raises(RuntimeError, match="S3 connection failed"):
            await service.download_file(created.file_id)


# ── Integration tests ─────────────────────────────────────────────


class TestServiceIntegration:
    async def test_full_lifecycle(self, service, repo, mock_s3):
        """Test upload, get, download, delete flow."""
        # Upload
        upload_result = await service.upload_file(
            category="vacation",
            subcategory="vacation_paid",
            entity_id=3,
            filename="vacation_form.docx",
            data=b"vacation form content",
            content_type="application/octet-stream",
        )
        file_id = upload_result.file_id

        # Get
        get_result = await service.get_file("vacation", "vacation_paid", 3)
        assert get_result is not None
        assert get_result.file_id == file_id
        assert get_result.filename == "vacation_form.docx"

        # Download
        mock_s3.download.return_value = b"vacation form content"
        data, filename = await service.download_file(file_id)
        assert data == b"vacation form content"
        assert filename == "vacation_form.docx"

        # Delete
        await service.delete_file(file_id)

        # Verify deleted
        assert await repo.get(file_id) is None
        mock_s3.delete.assert_awaited()

    async def test_multiple_entities_same_slot(self, service, repo, mock_s3):
        """Different entities can have files in the same category/subcategory slot."""
        # Upload for entity 1
        result1 = await service.upload_file(
            category="fire",
            subcategory="fire_resignation",
            entity_id=1,
            filename="fire_entity1.docx",
            data=b"content1",
            content_type="application/octet-stream",
        )

        # Upload for entity 2
        result2 = await service.upload_file(
            category="fire",
            subcategory="fire_resignation",
            entity_id=2,
            filename="fire_entity2.docx",
            data=b"content2",
            content_type="application/octet-stream",
        )

        # Both should exist
        get1 = await service.get_file("fire", "fire_resignation", 1)
        get2 = await service.get_file("fire", "fire_resignation", 2)

        assert get1 is not None
        assert get2 is not None
        assert get1.file_id == result1.file_id
        assert get2.file_id == result2.file_id
        assert get1.filename == "fire_entity1.docx"
        assert get2.filename == "fire_entity2.docx"

        # Should have 2 files total
        all_files = await service.get_all_files()
        assert len(all_files) == 2

    async def test_replace_preserves_other_entities(self, service, repo, mock_s3):
        """Replacing a file for one entity should not affect other entities."""
        # Upload for entity 1
        await service.upload_file(
            category="vacation",
            subcategory="vacation_paid",
            entity_id=1,
            filename="vacation1.docx",
            data=b"content1",
            content_type="application/octet-stream",
        )

        # Upload for entity 2
        result2 = await service.upload_file(
            category="vacation",
            subcategory="vacation_paid",
            entity_id=2,
            filename="vacation2.docx",
            data=b"content2",
            content_type="application/octet-stream",
        )

        # Replace entity 1's file
        await service.upload_file(
            category="vacation",
            subcategory="vacation_paid",
            entity_id=1,
            filename="vacation1_new.docx",
            data=b"content1_new",
            content_type="application/octet-stream",
        )

        # Entity 2 should still have original file
        get2 = await service.get_file("vacation", "vacation_paid", 2)
        assert get2 is not None
        assert get2.file_id == result2.file_id
        assert get2.filename == "vacation2.docx"

        # Entity 1 should have new file
        get1 = await service.get_file("vacation", "vacation_paid", 1)
        assert get1 is not None
        assert get1.filename == "vacation1_new.docx"
