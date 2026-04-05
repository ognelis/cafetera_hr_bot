"""Tests for app.rag.indexer — chunk preparation and Qdrant operations."""

from __future__ import annotations

from langchain_core.documents import Document as LCDocument

from app.rag.indexer import prepare_chunks

# ── prepare_chunks ────────────────────────────────────────────────


class TestPrepareChunks:
    def _make_chunks(self, n: int = 3) -> list[LCDocument]:
        return [
            LCDocument(
                page_content=f"chunk {i}",
                metadata={"source": "test.docx", "section": f"Heading {i}"},
            )
            for i in range(n)
        ]

    def test_enriches_metadata(self):
        raw = self._make_chunks(2)
        enriched = prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.docx",
            s3_key="documents/test.docx",
        )
        assert len(enriched) == 2
        for chunk in enriched:
            assert chunk.metadata["document_id"] == "doc-1"
            assert chunk.metadata["filename"] == "test.docx"
            assert chunk.metadata["s3_key"] == "documents/test.docx"
            assert chunk.metadata["is_search_enabled"] is True
            assert "chunk_id" in chunk.metadata

    def test_preserves_original_metadata(self):
        raw = self._make_chunks(1)
        enriched = prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.docx",
            s3_key="documents/test.docx",
        )
        assert enriched[0].metadata["source"] == "test.docx"
        assert enriched[0].metadata["section"] == "Heading 0"

    def test_page_content_preserved(self):
        raw = self._make_chunks(1)
        enriched = prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.docx",
            s3_key="documents/test.docx",
        )
        assert enriched[0].page_content == "chunk 0"

    def test_chunk_ids_are_unique(self):
        raw = self._make_chunks(5)
        enriched = prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.docx",
            s3_key="documents/test.docx",
        )
        ids = [c.metadata["chunk_id"] for c in enriched]
        assert len(set(ids)) == 5

    def test_search_disabled(self):
        raw = self._make_chunks(1)
        enriched = prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.docx",
            s3_key="documents/test.docx",
            is_search_enabled=False,
        )
        assert enriched[0].metadata["is_search_enabled"] is False

    def test_empty_input(self):
        enriched = prepare_chunks(
            [],
            document_id="doc-1",
            filename="test.docx",
            s3_key="documents/test.docx",
        )
        assert enriched == []

    def test_does_not_mutate_originals(self):
        raw = self._make_chunks(1)
        original_meta = dict(raw[0].metadata)
        prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.docx",
            s3_key="documents/test.docx",
        )
        assert raw[0].metadata == original_meta
