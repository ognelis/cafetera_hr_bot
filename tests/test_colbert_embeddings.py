"""Tests for ColBERT embedding adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.config import Settings
from app.rag.colbert_embeddings import (
    ColbertEmbeddingAdapter,
    build_colbert_embeddings,
)

# -- build_colbert_embeddings --


def test_build_colbert_embeddings_disabled_when_reranking_false():
    """When reranking_enabled=False, returns None."""
    settings = Settings(reranking_enabled=False, _env_file=None)
    result = build_colbert_embeddings(settings)
    assert result is None


def test_build_colbert_embeddings_returns_adapter_when_enabled():
    """When reranking_enabled=True, returns adapter."""
    settings = Settings(
        reranking_enabled=True,
        colbert_rerank_model="colbert-ir/colbertv2.0",
        _env_file=None,
    )

    mock_adapter = MagicMock()
    mock_adapter.dimension = 128

    with patch(
        "app.rag.colbert_embeddings.ColbertEmbeddingAdapter",
        return_value=mock_adapter,
    ) as mock_cls:
        result = build_colbert_embeddings(settings)

    mock_cls.assert_called_once_with(model_name="colbert-ir/colbertv2.0")
    assert result is mock_adapter


def test_build_colbert_embeddings_graceful_degradation_on_import_error():
    """When fastembed is not installed, returns None instead of raising."""
    settings = Settings(
        reranking_enabled=True,
        _env_file=None,
    )

    with patch(
        "app.rag.colbert_embeddings.ColbertEmbeddingAdapter",
        side_effect=ImportError("No module named 'fastembed'"),
    ):
        result = build_colbert_embeddings(settings)

    assert result is None


def test_build_colbert_embeddings_graceful_degradation_on_other_error():
    """When model loading fails for other reasons, returns None instead of raising."""
    settings = Settings(
        reranking_enabled=True,
        _env_file=None,
    )

    with patch(
        "app.rag.colbert_embeddings.ColbertEmbeddingAdapter",
        side_effect=RuntimeError("Model download failed"),
    ):
        result = build_colbert_embeddings(settings)

    assert result is None


# -- ColbertEmbeddingAdapter --


def test_colbert_adapter_embed_query_returns_list_of_lists():
    """embed_query() returns a 2D list: [num_tokens, dim]."""
    mock_model = MagicMock()
    mock_matrix = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]], dtype=np.float32)
    mock_model.embed.return_value = [mock_matrix]

    with patch("fastembed.LateInteractionTextEmbedding", return_value=mock_model):
        adapter = ColbertEmbeddingAdapter(model_name="test-model")

    result = adapter.embed_query("hello world")

    assert isinstance(result, list)
    assert len(result) == 3  # 3 tokens
    assert result[0] == pytest.approx([0.1, 0.2], abs=1e-6)
    assert result[1] == pytest.approx([0.3, 0.4], abs=1e-6)
    assert result[2] == pytest.approx([0.5, 0.6], abs=1e-6)


def test_colbert_adapter_embed_documents_returns_3d_list():
    """embed_documents() returns a 3D list: [num_docs, num_tokens, dim]."""
    mock_model = MagicMock()
    mock_doc1 = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)  # 2 tokens
    mock_doc2 = np.array([[0.5, 0.6], [0.7, 0.8], [0.9, 1.0]], dtype=np.float32)  # 3 tokens
    mock_model.embed.return_value = [mock_doc1, mock_doc2]

    with patch("fastembed.LateInteractionTextEmbedding", return_value=mock_model):
        adapter = ColbertEmbeddingAdapter(model_name="test-model")

    result = adapter.embed_documents(["doc1", "doc2"])

    assert isinstance(result, list)
    assert len(result) == 2  # 2 documents
    assert len(result[0]) == 2  # doc 1 has 2 tokens
    assert len(result[1]) == 3  # doc 2 has 3 tokens


def test_colbert_adapter_dimension_cached():
    """dimension property caches the result after first probe."""
    mock_model = MagicMock()
    mock_matrix = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)  # 1 token, 3-dim
    mock_model.embed.return_value = [mock_matrix]

    with patch("fastembed.LateInteractionTextEmbedding", return_value=mock_model):
        adapter = ColbertEmbeddingAdapter(model_name="test-model")

    dim1 = adapter.dimension
    dim2 = adapter.dimension

    assert dim1 == 3
    assert dim2 == 3
    assert mock_model.embed.call_count == 1
