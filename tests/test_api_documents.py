"""Tests for Block 12 — admin document API and HTML pages."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.document_service import DocumentService
from app.main import create_app
from app.storage.database import init_db
from app.storage.document_repo import DocumentRepository
from app.storage.models import DocumentRecord, DocumentStatus

TEST_API_KEY = "test-secret-key-12345"


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
    )


@pytest.fixture()
def mock_qdrant():
    client = MagicMock()
    client.delete = MagicMock()
    client.set_payload = MagicMock()
    client.count = MagicMock(return_value=MagicMock(count=0))
    client.close = MagicMock()
    return client


@pytest.fixture()
def mock_embeddings():
    return MagicMock()


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
def app(settings, mock_qdrant, mock_embeddings, mock_s3, db_path):
    """Create a test app with mocked Qdrant, embeddings, and S3."""
    application = create_app(settings)

    # Override lifespan-initialised resources
    repo = DocumentRepository(db_path)
    service = DocumentService(
        repo=repo,
        qdrant_client=mock_qdrant,
        embeddings=mock_embeddings,
        collection_name="test_collection",
    )
    application.state.qdrant_client = mock_qdrant
    application.state.embeddings = mock_embeddings
    application.state.doc_repo = repo
    application.state.doc_service = service
    application.state.s3 = mock_s3

    return application


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def auth_cookies():
    return {"admin_session": TEST_API_KEY}


@pytest.fixture()
async def repo(db_path):
    return DocumentRepository(db_path)


def _make_record(**overrides) -> DocumentRecord:
    now = datetime.now(UTC)
    defaults = {
        "document_id": uuid.uuid4().hex,
        "filename": "test.docx",
        "title": "Test document",
        "s3_key": "documents/test.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size_bytes": 12345,
        "status": DocumentStatus.completed,
        "is_search_enabled": True,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "indexed_at": now,
        "chunk_count": 5,
    }
    defaults.update(overrides)
    return DocumentRecord(**defaults)


# ── Auth tests ────────────────────────────────────────────────────


class TestAuth:
    def test_login_page_renders(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "Cafetera HR Admin" in resp.text

    def test_login_with_valid_key(self, client):
        resp = client.post(
            "/login",
            data={"api_key": TEST_API_KEY},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/documents"
        assert "admin_session" in resp.cookies

    def test_login_with_invalid_key(self, client):
        resp = client.post(
            "/login",
            data={"api_key": "wrong"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error=invalid_key" in resp.headers["location"]

    def test_documents_page_requires_auth(self, client):
        resp = client.get("/documents")
        assert resp.status_code == 403

    def test_api_requires_auth(self, client):
        resp = client.get("/api/documents")
        assert resp.status_code == 403

    def test_logout_clears_cookie(self, client, auth_cookies):
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"


# ── Documents page ────────────────────────────────────────────────


class TestDocumentsPage:
    def test_documents_page_renders(self, client, auth_cookies):
        resp = client.get("/documents", cookies=auth_cookies)
        assert resp.status_code == 200
        assert "Документы" in resp.text

    def test_documents_page_shows_empty_state(self, client, auth_cookies):
        resp = client.get("/documents", cookies=auth_cookies)
        assert resp.status_code == 200
        assert "Документов пока нет" in resp.text

    async def test_documents_page_shows_documents(
        self, client, auth_cookies, repo
    ):
        rec = _make_record()
        await repo.create(rec)
        resp = client.get("/documents", cookies=auth_cookies)
        assert resp.status_code == 200
        assert rec.title in resp.text


# ── List API ──────────────────────────────────────────────────────


class TestListDocuments:
    def test_empty_list(self, client, auth_cookies):
        resp = client.get("/api/documents", cookies=auth_cookies)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_documents(self, client, auth_cookies, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = client.get("/api/documents", cookies=auth_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["document_id"] == rec.document_id
        assert data[0]["title"] == rec.title


# ── Get document ──────────────────────────────────────────────────


class TestGetDocument:
    async def test_get_existing(self, client, auth_cookies, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = client.get(
            f"/api/documents/{rec.document_id}", cookies=auth_cookies
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == rec.title

    def test_get_nonexistent(self, client, auth_cookies):
        resp = client.get("/api/documents/nonexistent", cookies=auth_cookies)
        assert resp.status_code == 404


# ── Update title ──────────────────────────────────────────────────


class TestUpdateTitle:
    async def test_rename(self, client, auth_cookies, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = client.patch(
            f"/api/documents/{rec.document_id}/title",
            data={"title": "New Name"},
            cookies=auth_cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Name"

    async def test_rename_empty_rejected(self, client, auth_cookies, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = client.patch(
            f"/api/documents/{rec.document_id}/title",
            data={"title": "   "},
            cookies=auth_cookies,
        )
        assert resp.status_code == 422

    def test_rename_nonexistent(self, client, auth_cookies):
        resp = client.patch(
            "/api/documents/nonexistent/title",
            data={"title": "x"},
            cookies=auth_cookies,
        )
        assert resp.status_code == 404

    async def test_rename_htmx_returns_html(self, client, auth_cookies, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = client.patch(
            f"/api/documents/{rec.document_id}/title",
            data={"title": "HTMX Title"},
            cookies=auth_cookies,
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert "HTMX Title" in resp.text
        assert "<tr" in resp.text


# ── Toggle search ─────────────────────────────────────────────────


class TestToggleSearch:
    async def test_disable_search(self, client, auth_cookies, repo):
        rec = _make_record(is_search_enabled=True)
        await repo.create(rec)
        resp = client.patch(
            f"/api/documents/{rec.document_id}/search",
            data={"enabled": "false"},
            cookies=auth_cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["is_search_enabled"] is False

    async def test_enable_search(self, client, auth_cookies, repo):
        rec = _make_record(is_search_enabled=False)
        await repo.create(rec)
        resp = client.patch(
            f"/api/documents/{rec.document_id}/search",
            data={"enabled": "true"},
            cookies=auth_cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["is_search_enabled"] is True

    async def test_toggle_htmx_returns_html(self, client, auth_cookies, repo):
        rec = _make_record(is_search_enabled=True)
        await repo.create(rec)
        resp = client.patch(
            f"/api/documents/{rec.document_id}/search",
            data={"enabled": "false"},
            cookies=auth_cookies,
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert "<tr" in resp.text


# ── Delete ────────────────────────────────────────────────────────


class TestDeleteDocument:
    async def test_delete_existing(self, client, auth_cookies, repo, mock_s3):
        rec = _make_record()
        await repo.create(rec)

        resp = client.delete(
            f"/api/documents/{rec.document_id}", cookies=auth_cookies
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Verify deleted from repo
        fetched = await repo.get(rec.document_id)
        assert fetched is None

        # Verify S3 delete was called
        mock_s3.delete.assert_awaited_once_with(rec.s3_key)

    def test_delete_nonexistent(self, client, auth_cookies):
        resp = client.delete(
            "/api/documents/nonexistent", cookies=auth_cookies
        )
        assert resp.status_code == 404

    async def test_delete_htmx_returns_empty(
        self, client, auth_cookies, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        resp = client.delete(
            f"/api/documents/{rec.document_id}",
            cookies=auth_cookies,
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert resp.text == ""


# ── Upload ────────────────────────────────────────────────────────


class TestUpload:
    @patch("app.api.documents.load_docx", return_value=[])
    @patch("app.api.documents._index_in_background", new_callable=AsyncMock)
    async def test_upload_valid_file(
        self, mock_bg, mock_parse, client, auth_cookies, mock_s3
    ):
        fake_docx = BytesIO(b"PK\x03\x04fake docx content")
        resp = client.post(
            "/api/documents/upload",
            cookies=auth_cookies,
            files=[("files", ("test.docx", fake_docx, "application/octet-stream"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["uploaded"]) == 1
        assert data["uploaded"][0]["filename"] == "test.docx"
        assert data["errors"] == []

        # Verify S3 upload was called
        mock_s3.upload.assert_awaited_once()

    def test_upload_rejects_non_docx(self, client, auth_cookies):
        resp = client.post(
            "/api/documents/upload",
            cookies=auth_cookies,
            files=[("files", ("test.pdf", BytesIO(b"fake"), "application/pdf"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["uploaded"]) == 0
        assert len(data["errors"]) == 1
        assert "Unsupported" in data["errors"][0]["error"]

    def test_upload_rejects_empty_file(self, client, auth_cookies):
        resp = client.post(
            "/api/documents/upload",
            cookies=auth_cookies,
            files=[("files", ("empty.docx", BytesIO(b""), "application/octet-stream"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["errors"]) == 1
        assert "Empty" in data["errors"][0]["error"]

    def test_upload_requires_auth(self, client):
        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("test.docx", BytesIO(b"data"), "application/octet-stream"))],
        )
        assert resp.status_code == 403


# ── Partials ──────────────────────────────────────────────────────


class TestPartials:
    def test_table_partial_empty(self, client, auth_cookies):
        resp = client.get("/partials/document-table", cookies=auth_cookies)
        assert resp.status_code == 200
        assert "Документов пока нет" in resp.text

    async def test_table_partial_with_docs(self, client, auth_cookies, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = client.get("/partials/document-table", cookies=auth_cookies)
        assert resp.status_code == 200
        assert rec.title in resp.text

    async def test_row_partial(self, client, auth_cookies, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = client.get(
            f"/partials/document-row/{rec.document_id}", cookies=auth_cookies
        )
        assert resp.status_code == 200
        assert rec.title in resp.text

    def test_row_partial_nonexistent(self, client, auth_cookies):
        resp = client.get(
            "/partials/document-row/nonexistent", cookies=auth_cookies
        )
        assert resp.status_code == 200
        assert resp.text == ""

    def test_partials_require_auth(self, client):
        resp = client.get("/partials/document-table")
        assert resp.status_code == 403


# ── Download ──────────────────────────────────────────────────────


class TestDownload:
    async def test_download_existing(
        self, client, auth_cookies, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        # S3 mock returns file content and reports file exists
        mock_s3.exists.return_value = True
        mock_s3.download.return_value = b"file content here"

        resp = client.get(
            f"/api/documents/{rec.document_id}/download",
            cookies=auth_cookies,
        )
        assert resp.status_code == 200
        assert resp.content == b"file content here"
        mock_s3.download.assert_awaited_once_with(rec.s3_key)

    def test_download_nonexistent(self, client, auth_cookies):
        resp = client.get(
            "/api/documents/nonexistent/download", cookies=auth_cookies
        )
        assert resp.status_code == 404

    async def test_download_missing_file(
        self, client, auth_cookies, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        # S3 reports file does not exist
        mock_s3.exists.return_value = False

        resp = client.get(
            f"/api/documents/{rec.document_id}/download",
            cookies=auth_cookies,
        )
        assert resp.status_code == 404


# ── Reindex ───────────────────────────────────────────────────────


class TestReindex:
    @patch("app.api.documents.load_docx", return_value=[])
    async def test_reindex_starts(
        self, mock_parse, client, auth_cookies, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        # S3 reports file exists
        mock_s3.exists.return_value = True

        resp = client.post(
            f"/api/documents/{rec.document_id}/reindex",
            cookies=auth_cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "reindexing"

    def test_reindex_nonexistent(self, client, auth_cookies):
        resp = client.post(
            "/api/documents/nonexistent/reindex", cookies=auth_cookies
        )
        assert resp.status_code == 404

    async def test_reindex_missing_file(
        self, client, auth_cookies, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        # S3 reports file does not exist
        mock_s3.exists.return_value = False

        resp = client.post(
            f"/api/documents/{rec.document_id}/reindex",
            cookies=auth_cookies,
        )
        assert resp.status_code == 404
        assert "storage" in resp.json()["detail"]
