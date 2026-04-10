"""Tests for category files repository and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.category_file_service import CategoryFileService
from app.main import create_app
from app.storage.category_models import (
    CATEGORY_SLOTS,
    LEGAL_ENTITIES,
    CategoryFileRecord,
    is_valid_slot,
)
from app.storage.category_repo import CategoryFileRepository
from app.storage.database import init_db

TEST_API_KEY = "test-secret-key-12345"


# ── helpers ───────────────────────────────────────────────────────


def _make_category_record(**overrides) -> CategoryFileRecord:
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


# ── fixtures ──────────────────────────────────────────────────────


@pytest.fixture()
async def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


@pytest.fixture()
def settings(db_path):
    return Settings(
        admin_api_key=TEST_API_KEY,
        db_path=db_path,
        s3_endpoint_url="http://localhost:9000",
        s3_access_key="minioadmin",
        s3_secret_key="minioadmin",
        s3_bucket="test-bucket",
        qdrant_url="http://localhost:6333",
        _env_file=None,
    )


@pytest.fixture()
def mock_s3():
    """Mock S3Storage with async methods."""
    s3 = MagicMock()
    s3.upload = AsyncMock()
    s3.download = AsyncMock(return_value=b"file content here")
    s3.delete = AsyncMock()
    s3.exists = AsyncMock(return_value=False)
    s3.open = AsyncMock()
    s3.close = AsyncMock()
    return s3


@pytest.fixture()
def app(settings, mock_s3, db_path):
    """Create a test app with mocked S3."""
    application = create_app(settings)

    # Override lifespan-initialised resources
    repo = CategoryFileRepository(db_path)
    service = CategoryFileService(repo=repo, s3=mock_s3)
    application.state.s3 = mock_s3
    application.state.category_file_service = service

    return application


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def auth_cookies():
    return {"admin_session": TEST_API_KEY}


@pytest.fixture()
def auth_client(app, auth_cookies):
    """Authenticated client with cookies set on the instance."""
    c = TestClient(app, raise_server_exceptions=False)
    for key, value in auth_cookies.items():
        c.cookies.set(key, value)
    return c


@pytest.fixture()
async def repo(db_path):
    return CategoryFileRepository(db_path)


# ── Repository tests ──────────────────────────────────────────────


class TestRepositoryUpsertAndGet:
    async def test_upsert_and_get(self, repo):
        rec = _make_category_record()
        created = await repo.upsert(rec)
        assert created.file_id == rec.file_id
        assert created.category == "hire"
        assert created.subcategory == "hire_checklist"
        assert created.entity_id == 1
        assert created.filename == "test.docx"
        assert created.id is not None

        fetched = await repo.get(rec.file_id)
        assert fetched is not None
        assert fetched.file_id == rec.file_id
        assert fetched.category == "hire"
        assert fetched.subcategory == "hire_checklist"
        assert fetched.entity_id == 1
        assert fetched.filename == "test.docx"
        assert fetched.s3_key == rec.s3_key
        assert fetched.mime_type == rec.mime_type
        assert fetched.size_bytes == rec.size_bytes


class TestRepositoryGetBySlot:
    async def test_get_by_slot(self, repo):
        rec = _make_category_record(
            category="fire",
            subcategory="fire_checklist",
            entity_id=2,
        )
        await repo.upsert(rec)

        fetched = await repo.get_by_slot("fire", "fire_checklist", 2)
        assert fetched is not None
        assert fetched.file_id == rec.file_id
        assert fetched.category == "fire"
        assert fetched.subcategory == "fire_checklist"
        assert fetched.entity_id == 2

    async def test_get_by_slot_not_found(self, repo):
        result = await repo.get_by_slot("nonexistent", "slot", 1)
        assert result is None


class TestRepositoryListAll:
    async def test_list_all(self, repo):
        rec1 = _make_category_record(file_id=uuid.uuid4().hex, category="hire")
        rec2 = _make_category_record(file_id=uuid.uuid4().hex, category="fire")
        rec3 = _make_category_record(file_id=uuid.uuid4().hex, category="vacation")

        await repo.upsert(rec1)
        await repo.upsert(rec2)
        await repo.upsert(rec3)

        all_files = await repo.list_all()
        assert len(all_files) == 3
        file_ids = {f.file_id for f in all_files}
        assert file_ids == {rec1.file_id, rec2.file_id, rec3.file_id}


class TestRepositoryDelete:
    async def test_delete(self, repo):
        rec = _make_category_record()
        await repo.upsert(rec)

        # Verify exists
        fetched = await repo.get(rec.file_id)
        assert fetched is not None

        # Delete
        deleted = await repo.delete(rec.file_id)
        assert deleted is True

        # Verify gone
        fetched = await repo.get(rec.file_id)
        assert fetched is None

    async def test_delete_nonexistent(self, repo):
        deleted = await repo.delete("nonexistent-file-id")
        assert deleted is False


class TestRepositoryUniqueConstraintPerEntity:
    async def test_two_files_same_slot_different_entities(self, repo):
        """Two files for same category+subcategory but different entity_ids should coexist."""
        rec1 = _make_category_record(
            file_id=uuid.uuid4().hex,
            entity_id=1,
            s3_key="category-files/1/file1.docx",
        )
        rec2 = _make_category_record(
            file_id=uuid.uuid4().hex,
            entity_id=2,
            s3_key="category-files/2/file2.docx",
        )
        await repo.upsert(rec1)
        await repo.upsert(rec2)

        # Both should exist
        fetched1 = await repo.get_by_slot("hire", "hire_checklist", 1)
        fetched2 = await repo.get_by_slot("hire", "hire_checklist", 2)
        assert fetched1 is not None
        assert fetched2 is not None
        assert fetched1.file_id == rec1.file_id
        assert fetched2.file_id == rec2.file_id

    async def test_upsert_same_slot_replaces(self, repo):
        """Upserting same category+subcategory+entity_id should replace the first."""
        file_id1 = uuid.uuid4().hex
        file_id2 = uuid.uuid4().hex

        rec1 = _make_category_record(
            file_id=file_id1,
            entity_id=1,
            filename="old.docx",
            s3_key="category-files/1/old.docx",
        )
        rec2 = _make_category_record(
            file_id=file_id2,
            entity_id=1,
            filename="new.docx",
            s3_key="category-files/1/new.docx",
        )

        await repo.upsert(rec1)
        await repo.upsert(rec2)

        # Should only have the new one
        fetched = await repo.get_by_slot("hire", "hire_checklist", 1)
        assert fetched is not None
        assert fetched.file_id == file_id2
        assert fetched.filename == "new.docx"

        # Old one should not be findable by file_id (it was replaced)
        # But we can still check by listing all - should be just 1
        all_files = await repo.list_all()
        assert len(all_files) == 1
        assert all_files[0].file_id == file_id2


class TestIsValidSlot:
    def test_valid_slots(self):
        """Test various valid category/subcategory combinations."""
        for category, data in CATEGORY_SLOTS.items():
            for subcategory in data["subcategories"]:
                assert is_valid_slot(category, subcategory) is True

    def test_invalid_category(self):
        assert is_valid_slot("invalid", "hire_checklist") is False

    def test_invalid_subcategory(self):
        assert is_valid_slot("hire", "invalid_subcategory") is False

    def test_both_invalid(self):
        assert is_valid_slot("invalid", "invalid") is False

    def test_wrong_subcategory_for_category(self):
        """A valid subcategory from one category is invalid for another."""
        # fire_checklist is valid for fire, not for hire
        assert is_valid_slot("fire", "fire_checklist") is True
        assert is_valid_slot("hire", "fire_checklist") is False


# ── API tests ─────────────────────────────────────────────────────


class TestAPIAuth:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/category-files")
        assert resp.status_code == 403

    def test_slots_requires_auth(self, client):
        resp = client.get("/api/category-files/slots")
        assert resp.status_code == 403

    def test_upload_requires_auth(self, client):
        resp = client.post("/api/category-files/upload")
        assert resp.status_code == 403

    def test_download_requires_auth(self, client):
        resp = client.get("/api/category-files/some-id/download")
        assert resp.status_code == 403

    def test_delete_requires_auth(self, client):
        resp = client.delete("/api/category-files/some-id")
        assert resp.status_code == 403


class TestAPIListFiles:
    async def test_list_empty(self, auth_client):
        resp = auth_client.get("/api/category-files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_list_with_files(self, auth_client, repo):
        rec = _make_category_record(filename="myfile.docx")
        await repo.upsert(rec)

        resp = auth_client.get("/api/category-files")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["file_id"] == rec.file_id
        assert data["items"][0]["filename"] == "myfile.docx"
        assert data["items"][0]["category"] == "hire"
        assert data["items"][0]["entity_id"] == 1


class TestAPIListSlots:
    def test_slots_returns_categories_and_entities(self, auth_client):
        resp = auth_client.get("/api/category-files/slots")
        assert resp.status_code == 200
        data = resp.json()

        assert "categories" in data
        assert "entities" in data

        # Check categories match CATEGORY_SLOTS
        assert data["categories"] == CATEGORY_SLOTS

        # Check entities are properly formatted
        assert len(data["entities"]) == len(LEGAL_ENTITIES)
        for entity in data["entities"]:
            assert "id" in entity
            assert "name" in entity
            assert "short_name" in entity
            assert entity["id"] in LEGAL_ENTITIES


class TestAPIUpload:
    @patch.object(CategoryFileService, "upload_file")
    async def test_upload_valid_file(self, mock_upload, auth_client):
        mock_record = _make_category_record(filename="uploaded.docx")
        mock_upload.return_value = mock_record

        fake_docx = BytesIO(b"PK\x03\x04fake docx content")
        resp = auth_client.post(
            "/api/category-files/upload",
            data={
                "category": "hire",
                "subcategory": "hire_checklist",
                "entity_id": 1,
            },
            files={"file": ("test.docx", fake_docx, "application/octet-stream")},
        )
        assert resp.status_code == 200

        # Verify upload_file was called with correct args
        mock_upload.assert_awaited_once()
        call_kwargs = mock_upload.call_args.kwargs
        assert call_kwargs["category"] == "hire"
        assert call_kwargs["subcategory"] == "hire_checklist"
        assert call_kwargs["entity_id"] == 1
        assert call_kwargs["filename"] == "test.docx"

    def test_upload_invalid_slot(self, auth_client):
        fake_docx = BytesIO(b"PK\x03\x04fake docx content")
        resp = auth_client.post(
            "/api/category-files/upload",
            data={
                "category": "invalid",
                "subcategory": "invalid",
                "entity_id": 1,
            },
            files={"file": ("test.docx", fake_docx, "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "Invalid" in resp.json()["detail"]

    def test_upload_invalid_entity(self, auth_client):
        fake_docx = BytesIO(b"PK\x03\x04fake docx content")
        resp = auth_client.post(
            "/api/category-files/upload",
            data={
                "category": "hire",
                "subcategory": "hire_checklist",
                "entity_id": 999,
            },
            files={"file": ("test.docx", fake_docx, "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "Invalid" in resp.json()["detail"]

    def test_upload_rejects_non_docx(self, auth_client):
        resp = auth_client.post(
            "/api/category-files/upload",
            data={
                "category": "hire",
                "subcategory": "hire_checklist",
                "entity_id": 1,
            },
            files={"file": ("test.pdf", BytesIO(b"fake"), "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_upload_rejects_empty_file(self, auth_client):
        resp = auth_client.post(
            "/api/category-files/upload",
            data={
                "category": "hire",
                "subcategory": "hire_checklist",
                "entity_id": 1,
            },
            files={"file": ("empty.docx", BytesIO(b""), "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "Empty" in resp.json()["detail"]


class TestAPIDownload:
    @patch.object(CategoryFileService, "download_file")
    async def test_download_existing(self, mock_download, auth_client):
        mock_download.return_value = (b"file bytes", "myfile.docx")

        resp = auth_client.get("/api/category-files/some-file-id/download")
        assert resp.status_code == 200
        assert resp.content == b"file bytes"
        assert resp.headers["content-disposition"] == 'attachment; filename="myfile.docx"'

    @patch.object(CategoryFileService, "download_file")
    async def test_download_not_found(self, mock_download, auth_client):
        mock_download.side_effect = FileNotFoundError("File not found")

        resp = auth_client.get("/api/category-files/nonexistent/download")
        assert resp.status_code == 404


class TestAPIDelete:
    @patch.object(CategoryFileService, "delete_file")
    async def test_delete_existing(self, mock_delete, auth_client):
        resp = auth_client.delete("/api/category-files/some-file-id")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert data["file_id"] == "some-file-id"
        mock_delete.assert_awaited_once_with("some-file-id")

    @patch.object(CategoryFileService, "delete_file")
    async def test_delete_nonexistent(self, mock_delete, auth_client):
        """Delete should return success even if file doesn't exist (idempotent)."""
        resp = auth_client.delete("/api/category-files/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True


# ── HTML page tests ───────────────────────────────────────────────


class TestCategoryFilesPage:
    def test_page_requires_auth(self, client):
        resp = client.get("/category-files")
        assert resp.status_code == 403

    def test_page_renders(self, auth_client):
        resp = auth_client.get("/category-files")
        assert resp.status_code == 200
        assert "Категории" in resp.text or "category" in resp.text.lower()


# ── HTMX partial tests ────────────────────────────────────────────


class TestCategorySlotPartial:
    def test_partial_requires_auth(self, client):
        resp = client.get("/partials/category-slot/hire/hire_checklist/1")
        assert resp.status_code == 403

    @patch.object(CategoryFileService, "get_file")
    async def test_partial_with_file(self, mock_get_file, auth_client):
        mock_record = _make_category_record(filename="template.docx")
        mock_get_file.return_value = mock_record

        resp = auth_client.get("/partials/category-slot/hire/hire_checklist/1")
        assert resp.status_code == 200
        # Should contain filename
        assert "template.docx" in resp.text

    @patch.object(CategoryFileService, "get_file")
    async def test_partial_empty_slot(self, mock_get_file, auth_client):
        mock_get_file.return_value = None

        resp = auth_client.get("/partials/category-slot/hire/hire_checklist/1")
        assert resp.status_code == 200
