"""Tests for admin document API — bulk operations (reindex, bulk delete)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import _make_record

# ── Reindex ───────────────────────────────────────────────────────


class TestReindex:
    @patch("cafetera_admin.api.documents_upload._index_document_from_s3", new_callable=AsyncMock)
    async def test_reindex_starts(
        self, mock_bg, auth_client, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        # S3 reports file exists
        mock_s3.exists.return_value = True

        resp = auth_client.post(
            f"/api/documents/{rec.document_id}/reindex",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "reindexing"

    def test_reindex_nonexistent(self, auth_client):
        resp = auth_client.post(
            "/api/documents/nonexistent/reindex"
        )
        assert resp.status_code == 404

    async def test_reindex_missing_file(
        self, auth_client, repo, mock_s3
    ):
        rec = _make_record()
        await repo.create(rec)

        # S3 reports file does not exist
        mock_s3.exists.return_value = False

        resp = auth_client.post(
            f"/api/documents/{rec.document_id}/reindex",
        )
        assert resp.status_code == 404
        assert "storage" in resp.json()["detail"]
