"""ColBERT embedding adapter for reranking hybrid search.

Provides a thin wrapper around fastembed's LateInteractionTextEmbedding to produce
per-token (multivector) embeddings required by Qdrant's ColBERT
late-interaction reranking.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class ColbertEmbeddingAdapter:
    """Adapter that produces per-token ColBERT embeddings.

    ColBERT generates a list of vectors per text (one per token).
    Qdrant stores these as multivectors and performs late-interaction
    scoring during reranking.
    """

    def __init__(self, model_name: str) -> None:
        """Load the ColBERT model via fastembed.

        Args:
            model_name: HuggingFace model identifier, e.g.
                ``"colbert-ir/colbertv2.0"``.
        """
        try:
            from fastembed import LateInteractionTextEmbedding
        except ImportError as exc:
            raise ImportError(
                "ColBERT embeddings require fastembed. Run: uv sync"
            ) from exc

        self._model = LateInteractionTextEmbedding(model_name=model_name)
        self._dimension: int | None = None

    @property
    def dimension(self) -> int:
        """Return the per-token embedding dimension."""
        if self._dimension is None:
            # Probe the model with a short text
            result = list(self._model.embed(["probe"]))
            # result[0] is a 2D numpy array: [num_tokens, dim]
            self._dimension = result[0].shape[1]
        return self._dimension

    def embed_query(self, text: str) -> list[list[float]]:
        """Embed a single query into per-token vectors.

        Args:
            text: The query string.

        Returns:
            A list of per-token embedding vectors (2D: [num_tokens, dim]).
        """
        # fastembed.LateInteractionTextEmbedding.embed() yields one numpy array per input text.
        # Each array has shape (num_tokens, embedding_dim).
        embeddings = list(self._model.embed([text]))
        matrix = embeddings[0]  # 2D numpy array: [num_tokens, dim]
        return [row.tolist() for row in matrix]

    def embed_documents(self, texts: list[str]) -> list[list[list[float]]]:
        """Embed multiple documents into per-token vectors.

        Args:
            texts: List of document strings.

        Returns:
            A list of per-token embedding sets (3D: [num_docs, num_tokens, dim]).
        """
        all_embeddings = list(self._model.embed(texts))
        return [[row.tolist() for row in matrix] for matrix in all_embeddings]


def build_colbert_embeddings(settings: Settings) -> ColbertEmbeddingAdapter | None:
    """Build a ColBERT embedding adapter from settings.

    Returns ``None`` when reranking is disabled.

    Args:
        settings: Application settings.

    Returns:
        ``ColbertEmbeddingAdapter`` when reranking is enabled, otherwise
        ``None``.
    """
    if not settings.reranking_enabled:
        return None

    try:
        adapter = ColbertEmbeddingAdapter(model_name=settings.colbert_rerank_model)
        logger.info(
            "ColBERT embeddings initialized (model=%s, dim=%d)",
            settings.colbert_rerank_model,
            adapter.dimension,
        )
        return adapter
    except ImportError:
        logger.warning(
            "ColBERT model could not be loaded — "
            "falling back to dense+sparse without reranking",
            exc_info=True,
        )
        return None
    except Exception:
        logger.warning(
            "ColBERT embeddings unavailable — "
            "falling back to dense+sparse without reranking",
            exc_info=True,
        )
        return None
