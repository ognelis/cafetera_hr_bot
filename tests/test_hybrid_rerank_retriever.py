"""Tests for AsyncHybridRerankRetriever and factory dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np

from app.config import Settings
from app.rag.retriever import (
    AsyncHybridRerankRetriever,
    AsyncQdrantRetriever,
    build_retriever,
    build_retriever_for_document,
)


def _make_qdrant_client_mock() -> MagicMock:
    """Create a spec'd MagicMock that passes Pydantic's isinstance check."""
    from qdrant_client import AsyncQdrantClient

    return MagicMock(spec=AsyncQdrantClient)


def _make_sparse_result(indices: list[int], values: list[float]) -> MagicMock:
    """Create a mock sparse embedding result with .tolist() support."""
    idx_arr = np.array(indices)
    val_arr = np.array(values, dtype=np.float32)
    mock = MagicMock()
    mock.indices = MagicMock(spec=np.ndarray)
    mock.indices.tolist.return_value = idx_arr.tolist()
    mock.values = MagicMock(spec=np.ndarray)
    mock.values.tolist.return_value = val_arr.tolist()
    return mock


# -- AsyncHybridRerankRetriever --


async def test_async_hybrid_rerank_retriever_builds_prefetch_and_calls_query_points():
    """_aget_relevant_documents() builds Prefetch list and calls query_points
    with ColBERT rerank query.
    """
    mock_client = _make_qdrant_client_mock()
    mock_client.query_points = AsyncMock()

    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_query.return_value = [0.1, 0.2, 0.3]

    mock_sparse = MagicMock()
    mock_sparse.embed_query.return_value = _make_sparse_result([1, 2], [0.5, 0.5])

    mock_colbert = MagicMock()
    mock_colbert.embed_query.return_value = [[0.1, 0.2], [0.3, 0.4]]

    mock_result = MagicMock()
    mock_point = MagicMock()
    mock_point.payload = {
        "page_content": "test content",
        "metadata": {"doc_id": "123"},
    }
    mock_result.points = [mock_point]
    mock_client.query_points.return_value = mock_result

    retriever = AsyncHybridRerankRetriever(
        client=mock_client,
        collection_name="test_collection",
        embeddings=mock_embeddings,
        sparse_embedding=mock_sparse,
        colbert_embedding=mock_colbert,
        k=5,
        prefetch_limit=20,
    )

    from langchain_core.callbacks import AsyncCallbackManagerForRetrieverRun

    docs = await retriever._aget_relevant_documents(
        "test query",
        run_manager=AsyncMock(spec=AsyncCallbackManagerForRetrieverRun),
    )

    mock_client.query_points.assert_called_once()
    call_kwargs = mock_client.query_points.call_args.kwargs
    assert call_kwargs["collection_name"] == "test_collection"
    assert call_kwargs["using"] == "colbert"
    assert call_kwargs["limit"] == 5
    assert call_kwargs["with_payload"] is True

    prefetch = call_kwargs["prefetch"]
    assert len(prefetch) == 2

    assert len(docs) == 1
    assert docs[0].page_content == "test content"
    assert docs[0].metadata == {"doc_id": "123"}


async def test_async_hybrid_rerank_retriever_handles_empty_results():
    """_aget_relevant_documents() returns empty list when no points found."""
    mock_client = _make_qdrant_client_mock()
    mock_client.query_points = AsyncMock()
    mock_client.query_points.return_value = MagicMock(points=[])

    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_query.return_value = [0.1, 0.2]

    mock_sparse = MagicMock()
    mock_sparse.embed_query.return_value = _make_sparse_result([1], [0.5])

    mock_colbert = MagicMock()
    mock_colbert.embed_query.return_value = [[0.1, 0.2]]

    retriever = AsyncHybridRerankRetriever(
        client=mock_client,
        collection_name="test_collection",
        embeddings=mock_embeddings,
        sparse_embedding=mock_sparse,
        colbert_embedding=mock_colbert,
        k=5,
        prefetch_limit=20,
    )

    from langchain_core.callbacks import AsyncCallbackManagerForRetrieverRun

    docs = await retriever._aget_relevant_documents(
        "test query",
        run_manager=AsyncMock(spec=AsyncCallbackManagerForRetrieverRun),
    )

    assert docs == []


# -- Factory dispatch --


def test_build_retriever_dispatches_to_hybrid_when_enabled():
    """When reranking_enabled and colbert_embedding provided, returns
    AsyncHybridRerankRetriever.
    """
    settings = Settings(
        reranking_enabled=True,
        colbert_prefetch_limit=25,
        _env_file=None,
    )
    mock_client = _make_qdrant_client_mock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()
    mock_colbert = MagicMock()

    result = build_retriever(
        settings,
        qdrant_client=mock_client,
        embeddings=mock_embeddings,
        k=6,
        sparse_embedding=mock_sparse,
        colbert_embedding=mock_colbert,
    )

    assert isinstance(result, AsyncHybridRerankRetriever)
    assert result.k == 6
    assert result.prefetch_limit == 25
    assert result.sparse_embedding is mock_sparse
    assert result.colbert_embedding is mock_colbert


def test_build_retriever_returns_hybrid_when_reranking_disabled():
    """When reranking_enabled=False, returns AsyncQdrantRetriever (hybrid mode)."""
    settings = Settings(
        reranking_enabled=False,
        _env_file=None,
    )
    mock_client = _make_qdrant_client_mock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()
    mock_colbert = MagicMock()

    result = build_retriever(
        settings,
        qdrant_client=mock_client,
        embeddings=mock_embeddings,
        k=4,
        sparse_embedding=mock_sparse,
        colbert_embedding=mock_colbert,
    )

    assert isinstance(result, AsyncQdrantRetriever)
    assert result.k == 4


def test_build_retriever_returns_hybrid_when_colbert_missing():
    """When colbert_embedding is None, returns AsyncQdrantRetriever
    even if reranking_enabled.
    """
    settings = Settings(
        reranking_enabled=True,
        _env_file=None,
    )
    mock_client = _make_qdrant_client_mock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()

    result = build_retriever(
        settings,
        qdrant_client=mock_client,
        embeddings=mock_embeddings,
        k=4,
        sparse_embedding=mock_sparse,
        colbert_embedding=None,
    )

    assert isinstance(result, AsyncQdrantRetriever)


def test_build_retriever_for_document_dispatches_to_hybrid_when_enabled():
    """When reranking_enabled and colbert_embedding provided, returns
    AsyncHybridRerankRetriever for document-scoped retrieval.
    """
    settings = Settings(
        reranking_enabled=True,
        colbert_prefetch_limit=30,
        _env_file=None,
    )
    mock_client = _make_qdrant_client_mock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()
    mock_colbert = MagicMock()

    result = build_retriever_for_document(
        settings,
        "doc-123",
        qdrant_client=mock_client,
        embeddings=mock_embeddings,
        k=8,
        sparse_embedding=mock_sparse,
        colbert_embedding=mock_colbert,
    )

    assert isinstance(result, AsyncHybridRerankRetriever)
    assert result.k == 8
    assert result.prefetch_limit == 30

    assert result.filter is not None
    assert result.filter.must[0].key == "metadata.document_id"
    assert result.filter.must[0].match.value == "doc-123"


def test_build_retriever_for_document_returns_hybrid_when_disabled():
    """When reranking_enabled=False, returns AsyncQdrantRetriever."""
    settings = Settings(
        reranking_enabled=False,
        _env_file=None,
    )
    mock_client = _make_qdrant_client_mock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()
    mock_colbert = MagicMock()

    result = build_retriever_for_document(
        settings,
        "doc-456",
        qdrant_client=mock_client,
        embeddings=mock_embeddings,
        k=4,
        sparse_embedding=mock_sparse,
        colbert_embedding=mock_colbert,
    )

    assert isinstance(result, AsyncQdrantRetriever)
