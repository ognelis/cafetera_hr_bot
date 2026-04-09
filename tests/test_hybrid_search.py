"""Tests for hybrid search feature — sparse embeddings and retrieval mode."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.domain.qa_service import QAService
from app.rag.indexer import index_chunks
from app.rag.retriever import build_sparse_embeddings, build_vectorstore

# ── build_sparse_embeddings ───────────────────────────────────────


def test_build_sparse_embeddings_dense_mode():
    """When retrieval_mode="dense", build_sparse_embeddings() returns None."""
    settings = Settings(retrieval_mode="dense", _env_file=None)
    result = build_sparse_embeddings(settings)
    assert result is None


def test_build_sparse_embeddings_hybrid_mode():
    """When retrieval_mode="hybrid", build_sparse_embeddings() returns FastEmbedSparse."""
    settings = Settings(
        retrieval_mode="hybrid",
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


def test_build_sparse_embeddings_hybrid_missing_dependency():
    """When retrieval_mode="hybrid" but FastEmbedSparse import fails, raises ImportError."""
    settings = Settings(
        retrieval_mode="hybrid",
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

    assert "uv sync --extra hybrid" in str(exc_info.value)


# ── build_vectorstore ─────────────────────────────────────────────


def test_build_vectorstore_without_sparse():
    """build_vectorstore() called without sparse_embedding creates
    QdrantVectorStore without sparse_embedding kwarg."""
    mock_client = MagicMock()
    mock_embeddings = MagicMock()

    with patch("app.rag.retriever.QdrantVectorStore") as mock_vs_cls:
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

    with patch("app.rag.retriever.QdrantVectorStore") as mock_vs_cls:
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


def test_index_chunks_passes_sparse_embedding():
    """index_chunks() called with sparse_embedding passes it to QdrantVectorStore constructor."""
    mock_client = MagicMock()
    mock_embeddings = MagicMock()
    mock_sparse = MagicMock()

    mock_chunk = MagicMock()
    mock_chunk.model_copy.return_value = MagicMock(
        page_content="test content",
        metadata={},
    )

    # Patch where the import happens (langchain_qdrant.QdrantVectorStore)
    with patch("langchain_qdrant.QdrantVectorStore") as mock_vs_cls:
        index_chunks(
            client=mock_client,
            embeddings=mock_embeddings,
            collection_name="test_collection",
            chunks=[mock_chunk],
            sparse_embedding=mock_sparse,
        )

    mock_vs_cls.assert_called_once_with(
        client=mock_client,
        collection_name="test_collection",
        embedding=mock_embeddings,
        sparse_embedding=mock_sparse,
    )


# ── QAService ─────────────────────────────────────────────────────


def test_qa_service_stores_sparse_embedding():
    """QAService(sparse_embedding=mock_sparse) stores it as _sparse_embedding."""
    mock_sparse = MagicMock()
    service = QAService(sparse_embedding=mock_sparse)
    assert service._sparse_embedding is mock_sparse


# ── Settings defaults ─────────────────────────────────────────────


def test_settings_defaults():
    """Default retrieval_mode is 'dense', default sparse_embedding_model is 'Qdrant/bm25'."""
    settings = Settings(_env_file=None)
    assert settings.retrieval_mode == "dense"
    assert settings.sparse_embedding_model == "Qdrant/bm25"
