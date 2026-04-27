"""Tests for hybrid search feature — sparse embeddings and retrieval mode."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cafetera_admin.indexer import index_chunks
from cafetera_core.config import CoreSettings
from cafetera_core.domain.qa_service import QAService
from cafetera_core.rag.retriever import build_sparse_embeddings, build_vectorstore

# ── build_sparse_embeddings ───────────────────────────────────────


def test_build_sparse_embeddings_returns_fastembed():
    """build_sparse_embeddings() returns FastEmbedSparse."""
    settings = CoreSettings(
        sparse_embedding_model="Qdrant/bm25",
        _env_file=None,
    )

    mock_sparse = MagicMock()
    # Patch where the import happens (langchain_qdrant.FastEmbedSparse)
    with patch(
        "langchain_qdrant.FastEmbedSparse",
        return_value=mock_sparse,
    ) as mock_cls:
        result = build_sparse_embeddings(settings)

    mock_cls.assert_called_once_with(model_name="Qdrant/bm25")
    assert result is mock_sparse


def test_build_sparse_embeddings_missing_dependency():
    """When FastEmbedSparse import fails, raises ImportError."""
    settings = CoreSettings(
        sparse_embedding_model="Qdrant/bm25",
        _env_file=None,
    )

    # Make the import statement itself raise ImportError
    # This simulates when langchain_qdrant is not installed or FastEmbedSparse is not available
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "langchain_qdrant":
            raise ImportError("No module named 'fastembed'")
        return original_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", mock_import):
        with pytest.raises(ImportError) as exc_info:
            build_sparse_embeddings(settings)

    assert "fastembed" in str(exc_info.value)


# ── build_vectorstore ─────────────────────────────────────────────


def test_build_vectorstore_without_sparse():
    """build_vectorstore() called without sparse_embedding creates
    QdrantVectorStore without sparse_embedding kwarg."""
    mock_client = MagicMock()
    mock_embeddings = MagicMock()

    with patch("cafetera_core.rag.retriever.QdrantVectorStore") as mock_vs_cls:
        result = build_vectorstore(
            client=mock_client,
            embeddings=mock_embeddings,
            collection_name="test_collection",
            sparse_embedding=None,
        )

    mock_vs_cls.assert_called_once_with(
        client=mock_client,
        collection_name="test_collection",
        embedding=mock_embeddings,
    )
    assert result is mock_vs_cls.return_value


def test_build_vectorstore_with_sparse():
    """build_vectorstore() called with a sparse_embedding passes it to QdrantVectorStore."""
    mock_client = MagicMock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()

    with patch("cafetera_core.rag.retriever.QdrantVectorStore") as mock_vs_cls:
        result = build_vectorstore(
            client=mock_client,
            embeddings=mock_embeddings,
            collection_name="test_collection",
            sparse_embedding=mock_sparse,
        )

    mock_vs_cls.assert_called_once_with(
        client=mock_client,
        collection_name="test_collection",
        embedding=mock_embeddings,
        sparse_embedding=mock_sparse,
    )
    assert result is mock_vs_cls.return_value


# ── index_chunks ──────────────────────────────────────────────────


async def test_index_chunks_uses_sparse_embedding():
    """index_chunks() with sparse_embedding produces combined dense+sparse
    points in a single upsert using named vectors.
    """
    mock_client = AsyncMock()
    mock_embeddings = MagicMock()
    mock_embeddings.aembed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    mock_sparse = MagicMock()
    mock_sparse.embed_documents.return_value = [
        MagicMock(indices=[1, 2], values=[0.5, 0.5]),
    ]

    from langchain_core.documents import Document as LCDocument

    mock_chunk = LCDocument(
        page_content="test content",
        metadata={"chunk_id": "test-chunk-id-123"},
    )

    await index_chunks(
        client=mock_client,
        embeddings=mock_embeddings,
        collection_name="test_collection",
        chunks=[mock_chunk],
        sparse_embedding=mock_sparse,
    )

    # Single upsert with named dense + bm25 sparse vectors
    assert mock_client.upsert.call_count == 1
    call_kwargs = mock_client.upsert.call_args.kwargs
    assert call_kwargs["collection_name"] == "test_collection"
    point = call_kwargs["points"][0]
    assert "dense" in point.vector
    assert "bm25" in point.vector


async def test_index_chunks_dense_plus_sparse_named_vectors():
    """index_chunks() with sparse_embedding produces named vectors
    (dense + bm25) in a single upsert — no colbert vector.
    """
    import numpy as np

    mock_client = AsyncMock()
    mock_embeddings = MagicMock()
    mock_embeddings.aembed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

    mock_sparse = MagicMock()
    idx_arr = np.array([1, 2])
    val_arr = np.array([0.5, 0.5], dtype=np.float32)
    mock_sparse_result = MagicMock()
    mock_sparse_result.indices = MagicMock(spec=np.ndarray)
    mock_sparse_result.indices.tolist.return_value = idx_arr.tolist()
    mock_sparse_result.values = MagicMock(spec=np.ndarray)
    mock_sparse_result.values.tolist.return_value = val_arr.tolist()
    mock_sparse.embed_documents.return_value = [mock_sparse_result]

    from langchain_core.documents import Document as LCDocument

    mock_chunk = LCDocument(
        page_content="test content",
        metadata={"chunk_id": "test-chunk-id-456"},
    )

    await index_chunks(
        client=mock_client,
        embeddings=mock_embeddings,
        collection_name="test_collection",
        chunks=[mock_chunk],
        sparse_embedding=mock_sparse,
    )

    assert mock_client.upsert.call_count == 1
    call_kwargs = mock_client.upsert.call_args.kwargs
    point = call_kwargs["points"][0]
    assert "dense" in point.vector
    assert "bm25" in point.vector
    assert "colbert" not in point.vector


# ── QAService ─────────────────────────────────────────────────────


def test_qa_service_stores_sparse_embedding():
    """QAService(sparse_embedding=mock_sparse) stores it as _sparse_embedding."""
    mock_sparse = MagicMock()
    service = QAService(sparse_embedding=mock_sparse)
    assert service._sparse_embedding is mock_sparse


def test_qa_service_stores_reranker():
    """QAService(reranker=mock_reranker) stores it as _reranker."""
    mock_reranker = MagicMock()
    service = QAService(reranker=mock_reranker)
    assert service._reranker is mock_reranker


# ── Settings defaults ─────────────────────────────────────────────


def test_settings_defaults():
    """Default sparse_embedding_model is 'Qdrant/bm25'."""
    settings = CoreSettings(_env_file=None)
    assert settings.sparse_embedding_model == "Qdrant/bm25"


# ── Reranking settings ────────────────────────────────────────────


def test_reranking_settings_defaults():
    """Default reranking settings are disabled with sensible defaults."""
    settings = CoreSettings(_env_file=None)
    assert settings.reranking_enabled is False
    assert settings.reranker_model == "BAAI/bge-reranker-v2-m3"
    assert settings.reranker_prefetch_limit == 20
    assert settings.reranker_top_n == 5
