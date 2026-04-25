"""Tests for Block 12 — admin document API: list, detail, partials, pagination, filter/sort."""

from __future__ import annotations

from cafetera_core.storage.models import DocumentStatus
from tests.conftest import _make_record

# ── Documents page ────────────────────────────────────────────────


class TestDocumentsPage:
    def test_documents_page_renders(self, auth_client):
        resp = auth_client.get("/documents")
        assert resp.status_code == 200
        assert "Документы" in resp.text

    def test_documents_page_shows_empty_state(self, auth_client):
        resp = auth_client.get("/documents")
        assert resp.status_code == 200
        assert "Документов пока нет" in resp.text

    async def test_documents_page_shows_documents(
        self, auth_client, repo
    ):
        rec = _make_record()
        await repo.create(rec)
        resp = auth_client.get("/documents")
        assert resp.status_code == 200
        assert rec.title in resp.text


# ── List API ──────────────────────────────────────────────────────


class TestListDocuments:
    def test_empty_list(self, auth_client):
        resp = auth_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["pages"] == 0

    async def test_returns_documents(self, auth_client, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = auth_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["document_id"] == rec.document_id
        assert data["items"][0]["title"] == rec.title
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["pages"] == 1


# ── Get document ──────────────────────────────────────────────────


class TestGetDocument:
    async def test_get_existing(self, auth_client, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = auth_client.get(
            f"/api/documents/{rec.document_id}"
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == rec.title

    def test_get_nonexistent(self, auth_client):
        resp = auth_client.get("/api/documents/nonexistent")
        assert resp.status_code == 404


# ── Update title ──────────────────────────────────────────────────


class TestUpdateTitle:
    async def test_rename(self, auth_client, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = auth_client.patch(
            f"/api/documents/{rec.document_id}/title",
            data={"title": "New Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Name"

    async def test_rename_empty_rejected(self, auth_client, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = auth_client.patch(
            f"/api/documents/{rec.document_id}/title",
            data={"title": "   "},
        )
        assert resp.status_code == 422

    def test_rename_nonexistent(self, auth_client):
        resp = auth_client.patch(
            "/api/documents/nonexistent/title",
            data={"title": "x"},
        )
        assert resp.status_code == 404

    async def test_rename_htmx_returns_html(self, auth_client, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = auth_client.patch(
            f"/api/documents/{rec.document_id}/title",
            data={"title": "HTMX Title"},
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert "HTMX Title" in resp.text
        assert "<tr" in resp.text


# ── Toggle search ─────────────────────────────────────────────────


class TestToggleSearch:
    async def test_disable_search(self, auth_client, repo):
        rec = _make_record(is_search_enabled=True)
        await repo.create(rec)
        resp = auth_client.patch(
            f"/api/documents/{rec.document_id}/search",
            data={"enabled": "false"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_search_enabled"] is False

    async def test_enable_search(self, auth_client, repo):
        rec = _make_record(is_search_enabled=False)
        await repo.create(rec)
        resp = auth_client.patch(
            f"/api/documents/{rec.document_id}/search",
            data={"enabled": "true"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_search_enabled"] is True

    async def test_toggle_htmx_returns_html(self, auth_client, repo):
        rec = _make_record(is_search_enabled=True)
        await repo.create(rec)
        resp = auth_client.patch(
            f"/api/documents/{rec.document_id}/search",
            data={"enabled": "false"},
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert "<tr" in resp.text


# ── Delete ────────────────────────────────────────────────────────


class TestDeleteDocument:
    async def test_delete_existing(self, auth_client, repo, mock_s3):
        rec = _make_record()
        await repo.create(rec)

        resp = auth_client.delete(
            f"/api/documents/{rec.document_id}"
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Verify deleted from repo
        fetched = await repo.get(rec.document_id)
        assert fetched is None

        # Verify S3 delete was called
        mock_s3.delete.assert_awaited_once_with(rec.s3_key)

    def test_delete_nonexistent(self, auth_client):
        resp = auth_client.delete(
            "/api/documents/nonexistent"
        )
        assert resp.status_code == 404

    async def test_delete_htmx_returns_empty(
        self, auth_client, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        resp = auth_client.delete(
            f"/api/documents/{rec.document_id}",
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert resp.text == ""


# ── Partials ──────────────────────────────────────────────────────


class TestPartials:
    def test_table_partial_empty(self, auth_client):
        resp = auth_client.get("/partials/document-table")
        assert resp.status_code == 200
        assert "Документов пока нет" in resp.text

    async def test_table_partial_with_docs(self, auth_client, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = auth_client.get("/partials/document-table")
        assert resp.status_code == 200
        assert rec.title in resp.text

    async def test_row_partial(self, auth_client, repo):
        rec = _make_record()
        await repo.create(rec)
        resp = auth_client.get(
            f"/partials/document-row/{rec.document_id}"
        )
        assert resp.status_code == 200
        assert rec.title in resp.text

    def test_row_partial_nonexistent(self, auth_client):
        resp = auth_client.get(
            "/partials/document-row/nonexistent"
        )
        assert resp.status_code == 200
        assert resp.text == ""

    def test_partials_require_auth(self, client):
        resp = client.get("/partials/document-table")
        assert resp.status_code == 403


# ── Download ──────────────────────────────────────────────────────


class TestDownload:
    async def test_download_existing(
        self, auth_client, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        # S3 mock returns file content and reports file exists
        mock_s3.exists.return_value = True
        mock_s3.download.return_value = b"file content here"

        resp = auth_client.get(
            f"/api/documents/{rec.document_id}/download",
        )
        assert resp.status_code == 200
        assert resp.content == b"file content here"
        mock_s3.download.assert_awaited_once_with(rec.s3_key)

    def test_download_nonexistent(self, auth_client):
        resp = auth_client.get(
            "/api/documents/nonexistent/download"
        )
        assert resp.status_code == 404

    async def test_download_missing_file(
        self, auth_client, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        # S3 reports file does not exist
        mock_s3.exists.return_value = False

        resp = auth_client.get(
            f"/api/documents/{rec.document_id}/download",
        )
        assert resp.status_code == 404


# ── Pagination ────────────────────────────────────────────────────


class TestPagination:
    async def test_list_paginated_defaults(self, auth_client, repo):
        """GET /api/documents with no params returns items with pagination metadata."""
        # Create 5 documents
        for i in range(5):
            rec = _make_record(document_id=f"doc-{i}", title=f"Document {i}")
            await repo.create(rec)

        resp = auth_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["items"]) == 5
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["pages"] == 1

    async def test_list_paginated_with_params(self, auth_client, repo):
        """GET /api/documents?page=2&per_page=3 returns correct 3-item slice."""
        # Create 7 documents (ids will be 1-7, ordered by id DESC: 7,6,5,4,3,2,1)
        created_ids = []
        for i in range(7):
            rec = _make_record(document_id=f"doc-{i}", title=f"Document {i}")
            created = await repo.create(rec)
            created_ids.append(created.id)

        # Page 2 with per_page=3 should return items with ids 4, 3, 2 (0-indexed: positions 3,4,5)
        resp = auth_client.get("/api/documents?page=2&per_page=3")
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["items"]) == 3
        assert data["total"] == 7
        assert data["page"] == 2
        assert data["per_page"] == 3
        assert data["pages"] == 3  # 7 items / 3 per page = 2.33 -> 3 pages

        # Verify correct items returned (ordered by id DESC)
        # Page 1: ids 7, 6, 5
        # Page 2: ids 4, 3, 2
        actual_ids = [item["document_id"] for item in data["items"]]
        assert actual_ids == ["doc-3", "doc-2", "doc-1"]

    async def test_list_paginated_total_count(self, auth_client, repo):
        """Verify total field matches actual document count."""
        # Create documents one by one and verify total
        for i in range(10):
            rec = _make_record(document_id=f"doc-{i}", title=f"Document {i}")
            await repo.create(rec)

            resp = auth_client.get("/api/documents")
            data = resp.json()
            assert data["total"] == i + 1

    async def test_list_paginated_beyond_range(self, auth_client, repo):
        """GET /api/documents?page=100&per_page=5 returns empty items but correct total."""
        # Create 7 documents
        for i in range(7):
            rec = _make_record(document_id=f"doc-{i}", title=f"Document {i}")
            await repo.create(rec)

        resp = auth_client.get("/api/documents?page=100&per_page=5")
        assert resp.status_code == 200
        data = resp.json()

        assert data["items"] == []
        assert data["total"] == 7
        assert data["page"] == 100
        assert data["per_page"] == 5
        assert data["pages"] == 2  # 7 items / 5 per page = 1.4 -> 2 pages

    async def test_document_table_partial_pagination(self, auth_client, repo):
        """GET /partials/document-table with HX-Request returns pagination controls."""
        # Create 7 documents to trigger pagination (more than default per_page would be,
        # but we use per_page=3 to ensure multiple pages)
        for i in range(7):
            rec = _make_record(document_id=f"doc-{i}", title=f"Document {i}")
            await repo.create(rec)

        resp = auth_client.get(
            "/partials/document-table?page=1&per_page=3",
            headers={"HX-Request": "true"}
        )
        assert resp.status_code == 200

        # Check for pagination-related class names
        assert "join" in resp.text  # Pagination container class
        assert "join-item" in resp.text  # Pagination button class
        assert "btn-active" in resp.text  # Active page button class

        # Check for page number buttons (should have pages 1, 2, 3 for 7 items with per_page=3)
        # Page links contain hx-get attributes with page numbers
        assert 'hx-get="/partials/document-table?page=1&per_page=3"' in resp.text
        assert 'hx-get="/partials/document-table?page=2&per_page=3"' in resp.text
        assert 'hx-get="/partials/document-table?page=3&per_page=3"' in resp.text


# ── Filter & Sort API ─────────────────────────────────────────────


class TestFilterSortAPI:
    async def test_api_status_filter(self, auth_client, repo):
        """GET /api/documents?status=completed returns only completed docs."""
        r1 = _make_record(
            document_id="d1", status=DocumentStatus.completed,
        )
        r2 = _make_record(
            document_id="d2", status=DocumentStatus.pending,
        )
        await repo.create(r1)
        await repo.create(r2)

        resp = auth_client.get("/api/documents?status=completed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["document_id"] == "d1"
        assert data["status_filter"] == "completed"

    async def test_api_source_type_filter(self, auth_client, repo):
        """GET /api/documents?source_type=docx filters by extension."""
        r1 = _make_record(document_id="d1", filename="a.docx")
        r2 = _make_record(document_id="d2", filename="b.doc")
        await repo.create(r1)
        await repo.create(r2)

        resp = auth_client.get("/api/documents?source_type=docx")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["document_id"] == "d1"
        assert data["source_type_filter"] == "docx"

    async def test_api_sort_field_and_dir(self, auth_client, repo):
        """GET /api/documents?sort_field=title&sort_dir=asc sorts correctly."""
        r1 = _make_record(document_id="d1", title="Zebra")
        r2 = _make_record(document_id="d2", title="Apple")
        await repo.create(r1)
        await repo.create(r2)

        resp = auth_client.get(
            "/api/documents?sort_field=title&sort_dir=asc",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["title"] == "Apple"
        assert data["items"][1]["title"] == "Zebra"
        assert data["sort_field"] == "title"
        assert data["sort_dir"] == "asc"

    async def test_api_returns_filter_metadata(self, auth_client, repo):
        """Response includes status_filter, source_type_filter, sort fields."""
        resp = auth_client.get(
            "/api/documents?status=all&source_type=doc"
            "&sort_field=created_at&sort_dir=desc",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status_filter"] == "all"
        assert data["source_type_filter"] == "doc"
        assert data["sort_field"] == "created_at"
        assert data["sort_dir"] == "desc"

    async def test_partial_accepts_filter_params(self, auth_client, repo):
        """GET /partials/document-table accepts status & source_type."""
        r1 = _make_record(
            document_id="d1", status=DocumentStatus.completed,
        )
        r2 = _make_record(
            document_id="d2", status=DocumentStatus.pending,
        )
        await repo.create(r1)
        await repo.create(r2)

        resp = auth_client.get(
            "/partials/document-table?status=completed",
        )
        assert resp.status_code == 200
        assert "d1" in resp.text
        # pending doc should NOT appear in the filtered result
        assert "d2" not in resp.text

    async def test_documents_page_accepts_filter_params(
        self, auth_client, repo,
    ):
        """GET /documents accepts status, source_type, sort params."""
        r1 = _make_record(
            document_id="d1", status=DocumentStatus.completed,
        )
        r2 = _make_record(
            document_id="d2", status=DocumentStatus.pending,
        )
        await repo.create(r1)
        await repo.create(r2)

        resp = auth_client.get("/documents?status=completed")
        assert resp.status_code == 200
