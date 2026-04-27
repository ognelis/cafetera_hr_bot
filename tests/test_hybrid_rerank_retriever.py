"""Tests for RerankingRetriever, CrossEncoderReranker, and factory dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document

from cafetera_core.config import CoreSettings
from cafetera_core.rag.reranker import CrossEncoderReranker, RerankingRetriever
from cafetera_core.rag.retriever import (
    AsyncQdrantRetriever,
    build_retriever,
    build_retriever_for_document,
)


def _make_qdrant_client_mock() -> MagicMock:
    """Create a spec'd MagicMock that passes Pydantic's isinstance check."""
    from qdrant_client import AsyncQdrantClient

    return MagicMock(spec=AsyncQdrantClient)


# -- CrossEncoderReranker --


async def test_cross_encoder_reranker_arerank_returns_top_n():
    """arerank() calls CrossEncoder.predict and returns reranked docs."""
    docs = [
        Document(page_content="low relevance"),
        Document(page_content="high relevance"),
        Document(page_content="medium relevance"),
    ]

    mock_model = MagicMock()
    # predict returns scores for each pair
    mock_model.predict.return_value = [0.1, 0.95, 0.70]

    with patch(
        "cafetera_core.rag.reranker.CrossEncoder",
        return_value=mock_model,
    ):
        reranker = CrossEncoderReranker(model_name="test-model", top_n=2)

    result = await reranker.arerank("query", docs)

    assert len(result) == 2
    assert result[0].page_content == "high relevance"
    assert result[1].page_content == "medium relevance"
    mock_model.predict.assert_called_once()


async def test_cross_encoder_reranker_arerank_empty_docs():
    """arerank() returns empty list for empty input."""
    with patch("cafetera_core.rag.reranker.CrossEncoder"):
        reranker = CrossEncoderReranker(
            model_name="test-model", top_n=5
        )

    result = await reranker.arerank("query", [])
    assert result == []


async def test_cross_encoder_reranker_rerank_sync():
    """rerank() synchronously reranks documents."""
    docs = [
        Document(page_content="a"),
        Document(page_content="b"),
    ]

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.5, 0.9]

    with patch(
        "cafetera_core.rag.reranker.CrossEncoder",
        return_value=mock_model,
    ):
        reranker = CrossEncoderReranker(model_name="test-model", top_n=2)

    result = reranker.rerank("query", docs)

    assert len(result) == 2
    assert result[0].page_content == "b"
    assert result[1].page_content == "a"


# -- RerankingRetriever --


async def test_reranking_retriever_calls_base_then_reranker():
    """_aget_relevant_documents() calls base retriever then reranker."""
    base_docs = [
        Document(page_content="doc1"),
        Document(page_content="doc2"),
        Document(page_content="doc3"),
    ]
    reranked_docs = [
        Document(page_content="doc2"),
        Document(page_content="doc1"),
    ]

    from langchain_core.retrievers import BaseRetriever

    mock_base = MagicMock(spec=BaseRetriever)
    mock_base.ainvoke = AsyncMock(return_value=base_docs)

    mock_reranker = MagicMock(spec=CrossEncoderReranker)
    mock_reranker.arerank = AsyncMock(return_value=reranked_docs)

    retriever = RerankingRetriever(
        base_retriever=mock_base,
        reranker=mock_reranker,
    )

    from langchain_core.callbacks import AsyncCallbackManagerForRetrieverRun

    docs = await retriever._aget_relevant_documents(
        "test query",
        run_manager=AsyncMock(spec=AsyncCallbackManagerForRetrieverRun),
    )

    mock_base.ainvoke.assert_called_once_with("test query")
    mock_reranker.arerank.assert_called_once_with("test query", base_docs)
    assert docs == reranked_docs


# -- Factory dispatch --


def test_build_retriever_uses_prefetch_limit_when_reranking_enabled():
    """When reranking_enabled=True, build_retriever returns AsyncQdrantRetriever
    with k=reranker_prefetch_limit.
    """
    settings = CoreSettings(
        reranking_enabled=True,
        reranker_prefetch_limit=25,
        _env_file=None,
    )
    mock_client = _make_qdrant_client_mock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()

    result = build_retriever(
        settings,
        qdrant_client=mock_client,
        embeddings=mock_embeddings,
        k=6,
        sparse_embedding=mock_sparse,
    )

    assert isinstance(result, AsyncQdrantRetriever)
    # When reranking enabled, k should be reranker_prefetch_limit (25)
    assert result.k == 25


def test_build_retriever_uses_normal_k_when_reranking_disabled():
    """When reranking_enabled=False, returns AsyncQdrantRetriever with k."""
    settings = CoreSettings(
        reranking_enabled=False,
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
    )

    assert isinstance(result, AsyncQdrantRetriever)
    assert result.k == 4


def test_build_retriever_for_document_uses_prefetch_limit_when_enabled():
    """When reranking_enabled=True, build_retriever_for_document returns
    AsyncQdrantRetriever with k=reranker_prefetch_limit and document filter.
    """
    settings = CoreSettings(
        reranking_enabled=True,
        reranker_prefetch_limit=30,
        _env_file=None,
    )
    mock_client = _make_qdrant_client_mock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()

    result = build_retriever_for_document(
        settings,
        "doc-123",
        qdrant_client=mock_client,
        embeddings=mock_embeddings,
        k=8,
        sparse_embedding=mock_sparse,
    )

    assert isinstance(result, AsyncQdrantRetriever)
    # When reranking enabled, k should be reranker_prefetch_limit (30)
    assert result.k == 30
    assert result.filter is not None
    assert result.filter.must[0].key == "metadata.document_id"
    assert result.filter.must[0].match.value == "doc-123"


def test_build_retriever_for_document_uses_normal_k_when_disabled():
    """When reranking_enabled=False, returns AsyncQdrantRetriever with k."""
    settings = CoreSettings(
        reranking_enabled=False,
        _env_file=None,
    )
    mock_client = _make_qdrant_client_mock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()

    result = build_retriever_for_document(
        settings,
        "doc-456",
        qdrant_client=mock_client,
        embeddings=mock_embeddings,
        k=4,
        sparse_embedding=mock_sparse,
    )

    assert isinstance(result, AsyncQdrantRetriever)
    assert result.k == 4
