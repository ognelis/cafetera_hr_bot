"""Tests for hybrid search feature — sparse embeddings and retrieval mode."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.qa_service import QAService
from cafetera_rag_service.rag.retriever import build_sparse_embeddings

# ── build_sparse_embeddings ───────────────────────────────────────


def test_build_sparse_embeddings_returns_fastembed():
    """build_sparse_embeddings() returns FastEmbedSparse."""
    settings = RagServiceSettings(
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
    settings = RagServiceSettings(
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
    settings = RagServiceSettings(_env_file=None)
    assert settings.sparse_embedding_model == "Qdrant/bm25"


# ── Reranking settings ────────────────────────────────────────────


def test_reranking_settings_defaults():
    """Default reranking settings are disabled with sensible defaults."""
    settings = RagServiceSettings(_env_file=None)
    assert settings.reranking_enabled is False
    assert settings.reranker_url == "http://localhost:8082"
    assert settings.reranker_prefetch_limit == 20
    assert settings.reranker_top_n == 5
    assert settings.reranker_timeout == 30.0
