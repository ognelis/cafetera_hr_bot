"""Tests for app.rag.indexer — chunk preparation and Qdrant operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document as LCDocument

from app.rag.indexer import index_chunks, optimize_collection, prepare_chunks

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


# ── index_chunks ────────────────────────────────────────────────


class TestIndexChunks:
    def _make_chunks(self, n: int = 2) -> list[LCDocument]:
        return [
            LCDocument(
                page_content=f"chunk {i}",
                metadata={
                    "source": "test.docx",
                    "section": f"Heading {i}",
                    "document_id": "doc-1",
                    "chunk_id": f"chunk-{i}",
                    "filename": "test.docx",
                    "s3_key": "documents/test.docx",
                    "is_search_enabled": True,
                },
            )
            for i in range(n)
        ]

    @pytest.mark.asyncio
    async def test_is_search_enabled_at_top_level(self):
        """Verify is_search_enabled is stored as top-level field (not nested).

        Qdrant interprets dots inconsistently across operations:
        - upsert/set_payload: store literal keys
        - filters: traverse nested paths

        To avoid this ambiguity, is_search_enabled is stored as a simple
        top-level field with no dots in the key.
        """
        chunks = self._make_chunks(2)
        client = AsyncMock()
        embeddings = MagicMock()
        embeddings.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]

        await index_chunks(client, embeddings, "test-collection", chunks)

        # Verify upsert was called
        assert client.upsert.called
        points = client.upsert.call_args.kwargs["points"]

        # Check each point's payload
        for point in points:
            payload = point.payload
            # is_search_enabled MUST be at top-level, NOT nested in metadata
            assert "is_search_enabled" in payload
            assert payload["is_search_enabled"] is True
            # is_search_enabled MUST NOT be inside nested metadata dict
            assert "is_search_enabled" not in payload["metadata"]
            # No literal dotted key should exist
            assert "metadata.is_search_enabled" not in payload

    @pytest.mark.asyncio
    async def test_is_search_enabled_false_at_top_level(self):
        """Verify is_search_enabled=False is stored as top-level field."""
        chunks = [
            LCDocument(
                page_content="chunk 0",
                metadata={
                    "document_id": "doc-1",
                    "chunk_id": "chunk-0",
                    "filename": "test.docx",
                    "is_search_enabled": False,
                },
            ),
        ]
        client = AsyncMock()
        embeddings = MagicMock()
        embeddings.embed_documents.return_value = [[0.1, 0.2]]

        await index_chunks(client, embeddings, "test-collection", chunks)

        points = client.upsert.call_args.kwargs["points"]
        payload = points[0].payload

        # Verify is_search_enabled is at top level and False
        assert "is_search_enabled" in payload
        assert payload["is_search_enabled"] is False
        # NOT inside nested metadata
        assert "is_search_enabled" not in payload["metadata"]
        # No literal dotted key
        assert "metadata.is_search_enabled" not in payload

    @pytest.mark.asyncio
    async def test_other_metadata_preserved_in_nested_dict(self):
        """Verify other metadata fields remain in the nested metadata dict."""
        chunks = self._make_chunks(1)
        client = AsyncMock()
        embeddings = MagicMock()
        embeddings.embed_documents.return_value = [[0.1, 0.2]]

        await index_chunks(client, embeddings, "test-collection", chunks)

        points = client.upsert.call_args.kwargs["points"]
        payload = points[0].payload

        # Other metadata should still be in nested dict (but NOT is_search_enabled)
        assert payload["metadata"]["source"] == "test.docx"
        assert payload["metadata"]["section"] == "Heading 0"
        assert payload["metadata"]["document_id"] == "doc-1"
        assert payload["metadata"]["filename"] == "test.docx"
        assert payload["metadata"]["s3_key"] == "documents/test.docx"
        # is_search_enabled is at top level, not in metadata
        assert "is_search_enabled" not in payload["metadata"]

    @pytest.mark.asyncio
    async def test_empty_chunks_returns_zero(self):
        """Verify empty chunk list returns 0 without calling Qdrant."""
        client = AsyncMock()
        embeddings = MagicMock()

        result = await index_chunks(client, embeddings, "test-collection", [])

        assert result == 0
        assert not client.upsert.called


# ── optimize_collection ─────────────────────────────────────────────


class TestOptimizeCollection:
    @pytest.mark.asyncio
    async def test_sets_threshold_to_zero_then_restores(self):
        """Verify optimize_collection sets threshold=0 then restores it."""
        client = AsyncMock()
        # Simulate a green collection that is done optimizing
        mock_info = MagicMock()
        mock_info.status = "green"
        mock_info.optimizer_status = "ok"
        client.get_collection = AsyncMock(return_value=mock_info)

        await optimize_collection(client, "test-collection", indexing_threshold=10000)

        # Should have called update_collection twice:
        # 1st: set threshold=0 to force optimization
        # 2nd: restore threshold=10000
        assert client.update_collection.call_count == 2
        first_call = client.update_collection.call_args_list[0]
        second_call = client.update_collection.call_args_list[1]
        assert first_call.kwargs["optimizers_config"].indexing_threshold == 0
        assert second_call.kwargs["optimizers_config"].indexing_threshold == 10000
        assert first_call.kwargs["collection_name"] == "test-collection"
        assert second_call.kwargs["collection_name"] == "test-collection"

    @pytest.mark.asyncio
    async def test_polls_until_green(self):
        """Verify optimize_collection polls until status is green."""
        client = AsyncMock()
        # First poll: still optimizing, second: done
        optimizing_info = MagicMock()
        optimizing_info.status = "yellow"
        optimizing_info.optimizer_status = "optimizing"
        done_info = MagicMock()
        done_info.status = "green"
        done_info.optimizer_status = "ok"
        client.get_collection = AsyncMock(
            side_effect=[optimizing_info, done_info]
        )

        await optimize_collection(client, "test-collection")

        # Should have polled twice
        assert client.get_collection.call_count == 2
        # Still restores threshold after completion
        assert client.update_collection.call_count == 2

    @pytest.mark.asyncio
    async def test_restores_threshold_even_on_timeout(self):
        """Verify threshold is restored even if optimization doesn't complete."""
        client = AsyncMock()
        # Always return yellow — will hit the poll limit
        optimizing_info = MagicMock()
        optimizing_info.status = "yellow"
        optimizing_info.optimizer_status = "optimizing"
        client.get_collection = AsyncMock(return_value=optimizing_info)

        # Patch asyncio.sleep inside the indexer module to run instantly
        with patch("app.rag.indexer.asyncio.sleep", new_callable=AsyncMock):
            await optimize_collection(client, "test-collection")

        # Even though optimization never completed, threshold should be restored
        assert client.update_collection.call_count == 2
        restore_call = client.update_collection.call_args_list[-1]
        assert restore_call.kwargs["optimizers_config"].indexing_threshold == 10000
