"""Tests for admin document API — file upload and indexing."""

from __future__ import annotations

import zipfile
from io import BytesIO
from unittest.mock import AsyncMock, patch


def _make_minimal_docx_bytes() -> bytes:
    """Create a minimal valid DOCX file (ZIP with word/document.xml)."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "word/document.xml",
            "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
            "<w:body><w:p><w:r><w:t>Test</w:t></w:r></w:p></w:body></w:document>",
        )
        zf.writestr(
            "[Content_Types].xml",
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
            "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
            "<Default Extension='xml' ContentType='application/xml'/>"
            "<Override PartName='/word/document.xml'"
            " ContentType='application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document.main+xml'/>"
            "</Types>",
        )
    return buf.getvalue()


# ── Upload ────────────────────────────────────────────────────────


class TestUpload:
    @patch("app.api.documents.load_document", return_value=[])
    @patch("app.api.documents._index_document_from_s3", new_callable=AsyncMock)
    async def test_upload_valid_file(
        self, mock_bg, mock_parse, auth_client, mock_s3
    ):
        fake_docx = BytesIO(_make_minimal_docx_bytes())
        resp = auth_client.post(
            "/api/documents/upload",
            files=[("files", ("test.docx", fake_docx, "application/octet-stream"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["uploaded"]) == 1
        assert data["uploaded"][0]["filename"] == "test.docx"
        assert data["errors"] == []

        # Verify S3 upload was called
        mock_s3.upload.assert_awaited_once()

    def test_upload_rejects_non_docx(self, auth_client):
        resp = auth_client.post(
            "/api/documents/upload",
            files=[("files", ("test.pdf", BytesIO(b"fake"), "application/pdf"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["uploaded"]) == 0
        assert len(data["errors"]) == 1
        assert "Unsupported" in data["errors"][0]["error"]

    def test_upload_rejects_empty_file(self, auth_client):
        resp = auth_client.post(
            "/api/documents/upload",
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
