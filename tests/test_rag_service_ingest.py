"""Tests for RAG service ingest and toggle-search endpoints."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document as LCDocument

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.main import create_app
from cafetera_rag_service.parser import ParseResult
from cafetera_rag_service.resources import RagResources

TEST_API_KEY = "test-rag-key"


@pytest.fixture()
def rag_settings():
    return RagServiceSettings(
        rag_service_api_key=TEST_API_KEY,
        _env_file=None,
    )


@pytest.fixture()
def mock_rag_resources(rag_settings):
    """Create a RagResources with mocked components."""
    res = RagResources(settings=rag_settings)
    res.qdrant_client = AsyncMock()
    res.embeddings = AsyncMock()
    res.embeddings.aembed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    res.sparse_embeddings = None
    res.s3_storage = MagicMock()
    res.s3_storage.download = AsyncMock(return_value=b"file content")
    res.s3_storage.close = AsyncMock()
    return res


@pytest.fixture()
def rag_app(rag_settings, mock_rag_resources):
    """Create a test RAG service app with mocked resources."""

    @asynccontextmanager
    async def _test_lifespan(_app):
        _app.state.rag_resources = mock_rag_resources
        _app.state.settings = rag_settings
        _app.state.qa_services = {}
        yield

    app = create_app()
    app.router.lifespan_context = _test_lifespan
    return app


@pytest.fixture()
def rag_client(rag_app):
    with TestClient(rag_app, raise_server_exceptions=False) as c:
        yield c


# ── POST /api/index/ingest ─────────────────────────────────────────


class TestIngestEndpoint:
    @patch("cafetera_rag_service.api.ingest.load_document")
    async def test_ingest_success(
        self, mock_load_doc, rag_client, mock_rag_resources
    ):
        mock_load_doc.return_value = ParseResult(
            chunks=[
                LCDocument(
                    page_content="chunk 1",
                    metadata={
                        "source": "test.docx",
                        "headings": ["Section 1"],
                        "captions": [],
                        "page_numbers": [1],
                        "content_type": "text",
                        "section_path": "#/body/sections/0",
                    },
                ),
                LCDocument(
                    page_content="chunk 2",
                    metadata={
                        "source": "test.docx",
                        "headings": ["Section 2"],
                        "captions": [],
                        "page_numbers": [2],
                        "content_type": "text",
                        "section_path": "#/body/sections/1",
                    },
                ),
            ],
            page_count=10,
            binary_hash="hash123",
            extracted_title="Test Handbook",
        )
        mock_rag_resources.embeddings.aembed_documents.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]

        resp = rag_client.post(
            "/api/index/ingest",
            json={
                "document_id": "doc123",
                "filename": "test.docx",
                "s3_key": "documents/test.docx",
                "is_search_enabled": True,
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_indexed"] == 2
        assert data["page_count"] == 10
        assert data["binary_hash"] == "hash123"
        assert data["extracted_title"] == "Test Handbook"
        assert data["status"] == "ok"

        # Verify load_document was called with original_filename
        mock_load_doc.assert_called_once_with(
            ANY,  # tmp_path
            ANY,  # settings
            original_filename="test.docx",
        )
        # Verify S3 download was called
        mock_rag_resources.s3_storage.download.assert_awaited_once_with(
            "documents/test.docx"
        )
        # Verify old chunks were deleted first
        mock_rag_resources.qdrant_client.delete.assert_awaited_once()
        # Verify upsert was called
        mock_rag_resources.qdrant_client.upsert.assert_awaited()

    @patch("cafetera_rag_service.api.ingest.load_document")
    async def test_ingest_no_chunks(
        self, mock_load_doc, rag_client, mock_rag_resources
    ):
        mock_load_doc.return_value = ParseResult(
            chunks=[],
            page_count=0,
            binary_hash="emptyhash",
            extracted_title="Empty Doc",
        )

        resp = rag_client.post(
            "/api/index/ingest",
            json={
                "document_id": "doc-empty",
                "filename": "empty.docx",
                "s3_key": "documents/empty.docx",
                "is_search_enabled": True,
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_indexed"] == 0
        assert data["page_count"] == 0
        assert data["binary_hash"] == "emptyhash"
        assert data["extracted_title"] == "Empty Doc"

    def test_ingest_requires_auth(self, rag_client):
        resp = rag_client.post(
            "/api/index/ingest",
            json={
                "document_id": "doc123",
                "filename": "test.docx",
                "s3_key": "documents/test.docx",
            },
        )
        assert resp.status_code in (401, 403)


# ── _enrich_chunks unit tests ────────────────────────────────────────


class TestEnrichChunks:
    def test_enrich_chunks_preserves_metadata(self):
        """Verify _enrich_chunks merges parser metadata with document-level fields."""
        from cafetera_rag_service.api.ingest import _enrich_chunks

        chunks = [
            LCDocument(
                page_content="test chunk",
                metadata={
                    "source": "test.pdf",
                    "headings": ["Introduction"],
                    "captions": ["Table 1"],
                    "page_numbers": [1, 2],
                    "content_type": "table",
                    "section_path": "#/body/sections/0",
                },
            ),
        ]
        texts, metadatas = _enrich_chunks(
            chunks,
            document_id="doc-1",
            filename="test.pdf",
            s3_key="docs/test.pdf",
            is_search_enabled=True,
        )

        assert texts == ["test chunk"]
        assert len(metadatas) == 1
        meta = metadatas[0]
        # Document-level fields
        assert meta["document_id"] == "doc-1"
        assert meta["filename"] == "test.pdf"
        assert meta["s3_key"] == "docs/test.pdf"
        assert meta["is_search_enabled"] is True
        assert "chunk_id" in meta
        # Parser metadata preserved
        assert meta["headings"] == ["Introduction"]
        assert meta["captions"] == ["Table 1"]
        assert meta["page_numbers"] == [1, 2]
        assert meta["content_type"] == "table"
        assert meta["section_path"] == "#/body/sections/0"


# ── PATCH /api/index/documents/{document_id}/search ────────────────


class TestToggleSearchEndpoint:
    async def test_toggle_search_success(self, rag_client, mock_rag_resources):
        resp = rag_client.patch(
            "/api/index/documents/doc123/search",
            json={"is_search_enabled": False},
            headers={"X-API-Key": TEST_API_KEY},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify set_payload was called with correct filter
        mock_rag_resources.qdrant_client.set_payload.assert_awaited_once()
        call_kwargs = mock_rag_resources.qdrant_client.set_payload.call_args
        assert call_kwargs.kwargs["payload"] == {
            "is_search_enabled": False,
            "metadata.is_search_enabled": False,
        }

    async def test_toggle_search_enable(self, rag_client, mock_rag_resources):
        resp = rag_client.patch(
            "/api/index/documents/doc456/search",
            json={"is_search_enabled": True},
            headers={"X-API-Key": TEST_API_KEY},
        )

        assert resp.status_code == 200
        mock_rag_resources.qdrant_client.set_payload.assert_awaited_once()
        call_kwargs = mock_rag_resources.qdrant_client.set_payload.call_args
        assert call_kwargs.kwargs["payload"] == {
            "is_search_enabled": True,
            "metadata.is_search_enabled": True,
        }

    def test_toggle_search_requires_auth(self, rag_client):
        resp = rag_client.patch(
            "/api/index/documents/doc123/search",
            json={"is_search_enabled": False},
        )
        assert resp.status_code in (401, 403)
