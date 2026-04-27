"""Tests for app.rag.indexer — chunk preparation and Qdrant operations."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from langchain_core.documents import Document as LCDocument
from qdrant_client.http.exceptions import ResponseHandlingException

from cafetera_admin.indexer import (
    _INDEXING_THRESHOLD,
    _upsert_with_retry,
    index_chunks,
    optimize_collection,
    prepare_chunks,
)

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

    def test_extracts_dl_meta_page_numbers_and_headings(self):
        raw = [
            LCDocument(
                page_content="chunk",
                metadata={
                    "source": "test.pdf",
                    "dl_meta": {
                        "page_numbers": [1, 2],
                        "headings": ["Intro", "Section 1"],
                    },
                },
            ),
        ]
        enriched = prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.pdf",
            s3_key="documents/test.pdf",
        )
        assert enriched[0].metadata["page_numbers"] == [1, 2]
        assert enriched[0].metadata["headings"] == ["Intro", "Section 1"]

    def test_extracts_dl_meta_singular_page_number_and_heading(self):
        raw = [
            LCDocument(
                page_content="chunk",
                metadata={
                    "source": "test.pdf",
                    "dl_meta": {
                        "page_number": 3,
                        "heading": "Chapter 2",
                    },
                },
            ),
        ]
        enriched = prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.pdf",
            s3_key="documents/test.pdf",
        )
        assert enriched[0].metadata["page_number"] == 3
        assert enriched[0].metadata["heading"] == "Chapter 2"

    def test_plain_chunks_without_dl_meta(self):
        raw = [
            LCDocument(
                page_content="chunk",
                metadata={"source": "test.docx", "section": "Heading"},
            ),
        ]
        enriched = prepare_chunks(
            raw,
            document_id="doc-1",
            filename="test.docx",
            s3_key="documents/test.docx",
        )
        assert "page_numbers" not in enriched[0].metadata
        assert "headings" not in enriched[0].metadata
        assert enriched[0].metadata["source"] == "test.docx"
        assert enriched[0].metadata["section"] == "Heading"


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
        embeddings.aembed_documents = AsyncMock(
            return_value=[[0.1, 0.2], [0.3, 0.4]]
        )

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
        embeddings.aembed_documents = AsyncMock(
            return_value=[[0.1, 0.2]]
        )

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
        embeddings.aembed_documents = AsyncMock(
            return_value=[[0.1, 0.2]]
        )

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
        with patch("cafetera_admin.indexer.asyncio.sleep", new_callable=AsyncMock):
            await optimize_collection(client, "test-collection")

        # Even though optimization never completed, threshold should be restored
        assert client.update_collection.call_count == 2
        restore_call = client.update_collection.call_args_list[-1]
        assert restore_call.kwargs["optimizers_config"].indexing_threshold == 10000


# ── index_chunks batching ──────────────────────────────────────────


class TestIndexChunksBatching:
    """Tests for batched upsert and deferred indexing in index_chunks."""

    def _make_chunks(self, n: int) -> list[LCDocument]:
        return [
            LCDocument(
                page_content=f"chunk {i}",
                metadata={
                    "source": "test.docx",
                    "document_id": "doc-1",
                    "chunk_id": f"chunk-{i}",
                    "filename": "test.docx",
                    "s3_key": "documents/test.docx",
                    "is_search_enabled": True,
                },
            )
            for i in range(n)
        ]

    def _mock_embeddings(self, n: int) -> MagicMock:
        embeddings = MagicMock()
        embeddings.aembed_documents = AsyncMock(
            return_value=[[0.1] * 4 for _ in range(n)]
        )
        return embeddings

    @pytest.mark.asyncio
    async def test_batched_upserts(self):
        """When chunks > batch_size, upsert is called multiple times."""
        n = 5
        batch_size = 2
        chunks = self._make_chunks(n)
        client = AsyncMock()
        embeddings = self._mock_embeddings(n)

        result = await index_chunks(
            client, embeddings, "col", chunks, batch_size=batch_size,
        )

        assert result == n
        expected_batches = math.ceil(n / batch_size)
        assert client.upsert.call_count == expected_batches

        # All points are upserted across batches
        all_points = []
        for c in client.upsert.call_args_list:
            all_points.extend(c.kwargs["points"])
        assert len(all_points) == n

    @pytest.mark.asyncio
    async def test_batched_upserts_deferred_indexing(self):
        """Deferred indexing: threshold=0 before batches, restored after."""
        chunks = self._make_chunks(5)
        client = AsyncMock()
        embeddings = self._mock_embeddings(5)

        await index_chunks(
            client, embeddings, "col", chunks, batch_size=2,
        )

        assert client.update_collection.call_count == 2
        first = client.update_collection.call_args_list[0]
        second = client.update_collection.call_args_list[1]
        assert first.kwargs["optimizers_config"].indexing_threshold == 0
        assert (
            second.kwargs["optimizers_config"].indexing_threshold
            == _INDEXING_THRESHOLD
        )

    @pytest.mark.asyncio
    async def test_single_batch_no_deferred_indexing(self):
        """When chunks <= batch_size, one upsert, no update_collection."""
        chunks = self._make_chunks(3)
        client = AsyncMock()
        embeddings = self._mock_embeddings(3)

        result = await index_chunks(
            client, embeddings, "col", chunks, batch_size=64,
        )

        assert result == 3
        assert client.upsert.call_count == 1
        client.update_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_deferred_indexing_restored_on_error(self):
        """Threshold restored in finally even when upsert raises."""
        chunks = self._make_chunks(5)
        client = AsyncMock()
        # First upsert succeeds, second raises
        client.upsert.side_effect = [None, RuntimeError("boom")]
        embeddings = self._mock_embeddings(5)

        with pytest.raises(RuntimeError, match="boom"):
            await index_chunks(
                client, embeddings, "col", chunks, batch_size=2,
            )

        # Threshold must still be restored (finally block)
        restore_calls = [
            c
            for c in client.update_collection.call_args_list
            if c.kwargs["optimizers_config"].indexing_threshold
            == _INDEXING_THRESHOLD
        ]
        assert len(restore_calls) == 1

    @pytest.mark.asyncio
    async def test_parallel_embeddings_dense_and_sparse(self):
        """Dense and sparse embeddings run concurrently."""
        chunks = self._make_chunks(2)
        client = AsyncMock()
        embeddings = self._mock_embeddings(2)

        sparse_emb = MagicMock()
        sparse_vec = MagicMock()
        sparse_vec.indices = [0, 1]
        sparse_vec.values = [0.5, 0.6]
        sparse_emb.embed_documents.return_value = [sparse_vec, sparse_vec]

        await index_chunks(
            client,
            embeddings,
            "col",
            chunks,
            sparse_embedding=sparse_emb,
        )

        embeddings.aembed_documents.assert_called_once()
        sparse_emb.embed_documents.assert_called_once()

        points = client.upsert.call_args.kwargs["points"]
        for p in points:
            assert "dense" in p.vector
            assert "bm25" in p.vector
            assert "colbert" not in p.vector


# ── _upsert_with_retry ─────────────────────────────────────────────


class TestUpsertWithRetry:
    """Tests for the retry wrapper around Qdrant upsert."""

    def _make_points(self, n: int = 2) -> list:
        from qdrant_client import models

        return [
            models.PointStruct(
                id=f"pt-{i}", vector={"dense": [0.1, 0.2]}, payload={},
            )
            for i in range(n)
        ]

    async def test_upsert_succeeds_first_attempt(self):
        client = AsyncMock()
        points = self._make_points()

        await _upsert_with_retry(client, "col", points)

        client.upsert.assert_called_once_with(
            collection_name="col", points=points,
        )

    async def test_upsert_retries_on_response_handling_exception(self, caplog):
        client = AsyncMock()
        client.upsert.side_effect = [
            ResponseHandlingException("timeout"),
            None,
        ]
        points = self._make_points()

        with patch(
            "cafetera_admin.indexer.asyncio.sleep", new_callable=AsyncMock,
        ):
            await _upsert_with_retry(client, "col", points)

        assert client.upsert.call_count == 2
        assert any("retrying" in r.message.lower() for r in caplog.records)

    async def test_upsert_retries_on_httpx_read_error(self, caplog):
        client = AsyncMock()
        client.upsert.side_effect = [
            httpx.ReadError("connection reset"),
            None,
        ]
        points = self._make_points()

        with patch(
            "cafetera_admin.indexer.asyncio.sleep", new_callable=AsyncMock,
        ):
            await _upsert_with_retry(client, "col", points)

        assert client.upsert.call_count == 2
        assert any("retrying" in r.message.lower() for r in caplog.records)

    async def test_upsert_raises_after_max_retries(self):
        client = AsyncMock()
        client.upsert.side_effect = ResponseHandlingException("timeout")
        points = self._make_points()
        max_retries = 3

        with (
            patch(
                "cafetera_admin.indexer.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            pytest.raises(ResponseHandlingException),
        ):
            await _upsert_with_retry(
                client, "col", points, max_retries=max_retries,
            )

        # initial attempt + max_retries - 1 retries = max_retries total
        assert client.upsert.call_count == max_retries

    async def test_upsert_retry_uses_exponential_backoff(self):
        client = AsyncMock()
        client.upsert.side_effect = ResponseHandlingException("timeout")
        points = self._make_points()
        max_retries = 4

        with (
            patch(
                "cafetera_admin.indexer.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
            pytest.raises(ResponseHandlingException),
        ):
            await _upsert_with_retry(
                client, "col", points, max_retries=max_retries,
            )

        # Backoff: 2^1, 2^2, 2^3 (last attempt re-raises, no sleep)
        assert mock_sleep.call_count == max_retries - 1
        for i, call in enumerate(mock_sleep.call_args_list):
            expected = 2 ** (i + 1)
            assert call.args[0] == expected
