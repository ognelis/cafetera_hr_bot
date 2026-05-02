"""Dense retriever backed by Qdrant vector store."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict
from qdrant_client import AsyncQdrantClient, models

from cafetera_rag_service.rag.text_processor import preprocess_russian


def _to_list(value) -> list:
    """Convert numpy array or passthrough plain list to Python list."""
    return value.tolist() if hasattr(value, "tolist") else value


class CollectionNotFoundError(Exception):
    """Raised when the target Qdrant collection does not exist yet."""


class AsyncQdrantRetriever(BaseRetriever):
    """Async retriever using Qdrant's AsyncQdrantClient directly.

    Replaces LangChain's QdrantVectorStore for retrieval to enable
    fully async operations without sync client overhead.

    When ``sparse_embedding`` is provided, performs hybrid search
    using dense + BM25 prefetch fused by Reciprocal Rank Fusion (RRF).
    Otherwise falls back to dense-only.
    """

    client: AsyncQdrantClient
    collection_name: str
    embeddings: Any
    sparse_embedding: Any = None
    lemmatize: bool = False
    k: int = 5
    prefetch_limit: int = 20
    filter: models.Filter | None = None
    score_threshold: float | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Retrieve relevant documents asynchronously."""
        query_vector = await self.embeddings.aembed_query(query)

        sparse_query = preprocess_russian(query) if self.lemmatize else query

        if self.sparse_embedding is not None and sparse_query.strip():
            # Hybrid search: dense + BM25 prefetch, fused by RRF
            from qdrant_client.models import Prefetch, Rrf, RrfQuery, SparseVector

            sparse_result = self.sparse_embedding.embed_query(sparse_query)
            sparse_vec = SparseVector(
                indices=_to_list(sparse_result.indices),
                values=_to_list(sparse_result.values),
            )
            prefetch = [
                Prefetch(
                    query=query_vector,
                    using="dense",
                    limit=self.prefetch_limit,
                    score_threshold=self.score_threshold,
                ),
                Prefetch(query=sparse_vec, using="bm25", limit=self.prefetch_limit),
            ]
            results = await self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query=RrfQuery(rrf=Rrf()),
                limit=self.k,
                query_filter=self.filter,
            )
            # Fallback: if hybrid returned nothing (both dense threshold and
            # BM25 found nothing), retry dense-only without threshold.
            if not results.points and self.score_threshold is not None:
                logger.debug(
                    "Hybrid search returned 0 results (threshold=%.2f), "
                    "falling back to dense top-1 without threshold",
                    self.score_threshold,
                )
                results = await self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    using="dense",
                    limit=1,
                    query_filter=self.filter,
                )
            points = results.points
        else:
            # Dense-only search (also used when sparse query is empty after
            # stop-word removal to avoid zero-vector BM25 prefetch).
            if self.sparse_embedding is not None and not sparse_query.strip():
                logger.debug("Sparse query empty after preprocessing, falling back to dense-only")
            results = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                limit=self.k,
                query_filter=self.filter,
            )
            # Client-side filtering with min-1 guarantee
            points = results.points
            if self.score_threshold is not None and points:
                filtered = [r for r in points if r.score >= self.score_threshold]
                if filtered:
                    points = filtered
                else:
                    logger.debug(
                        "All %d dense results below threshold %.2f, "
                        "keeping top-1 (score=%.3f)",
                        len(results.points),
                        self.score_threshold,
                        results.points[0].score,
                    )
                    points = [results.points[0]]

        docs: list[Document] = []
        for r in points:
            if r.payload is not None:
                docs.append(
                    Document(
                        page_content=r.payload.get("page_content", ""),
                        metadata=r.payload.get("metadata", {}) or {},
                    )
                )
        return docs

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Sync retrieval is not supported - use async API only."""
        raise NotImplementedError("Use async API only")


def estimate_k(question: str, *, max_k: int = 10) -> int:
    """Estimate the number of chunks to retrieve based on question complexity.

    Rules:
    - Short questions (<=5 words): k=4
    - Medium questions (6-15 words): k=6
    - Long/complex questions (>15 words): k=max_k
    """
    word_count = len(question.split())
    if word_count <= 5:
        return 4
    elif word_count <= 15:
        return 6
    return max_k

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

    from cafetera_rag_service.config import RagServiceSettings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hr_documents"


def build_qdrant_client(settings: RagServiceSettings) -> AsyncQdrantClient:
    """Create an async Qdrant client from settings.

    Configures explicit timeout to prevent httpx.ReadError during
    large upsert operations (e.g. batch document indexing).
    """
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=settings.qdrant_timeout,  # type: ignore[arg-type]
    )


def build_embeddings(settings: RagServiceSettings) -> Embeddings:
    """Create an embedding model based on ``settings.embedding_provider``."""
    if settings.embedding_provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,  # type: ignore[arg-type]
            base_url=settings.embedding_base_url or None,
        )

    if settings.embedding_provider == "llamacpp":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.embedding_api_key or "no-key",  # type: ignore[arg-type]
            base_url=settings.embedding_base_url or "http://localhost:8080/v1",
        )

    # Default: Ollama
    try:
        from langchain_ollama import OllamaEmbeddings
    except ImportError as exc:
        raise ImportError(
            "Install the 'ollama' extra: uv sync --extra ollama"
        ) from exc
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
    )


def build_sparse_embeddings(settings: RagServiceSettings):
    """Build sparse embeddings for hybrid search."""
    try:
        from langchain_qdrant import FastEmbedSparse
    except ImportError as exc:
        raise ImportError(
            "fastembed is not installed. Run: uv sync"
        ) from exc
    try:
        return FastEmbedSparse(model_name=settings.sparse_embedding_model)
    except (ImportError, ValueError) as exc:
        raise ImportError(
            "Failed to load sparse embedding model. Run: uv sync"
        ) from exc


def build_retriever(
    settings: RagServiceSettings,
    *,
    qdrant_client: AsyncQdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str = COLLECTION_NAME,
    k: int = 4,
    sparse_embedding=None,
) -> AsyncQdrantRetriever:
    """Build an async retriever over the given Qdrant collection.

    Returns a hybrid ``AsyncQdrantRetriever`` (dense + sparse).
    When ``settings.reranking_enabled``, uses a larger ``k`` equal to
    ``reranker_prefetch_limit`` so the downstream HTTP reranker
    reranker receives enough candidates.

    Only chunks where ``is_search_enabled`` is not explicitly ``False``
    are returned.
    """
    if qdrant_client is None:
        qdrant_client = build_qdrant_client(settings)
    if embeddings is None:
        embeddings = build_embeddings(settings)

    search_filter = models.Filter(
        must_not=[
            models.FieldCondition(
                key="is_search_enabled",
                match=models.MatchValue(value=False),
            )
        ]
    )

    effective_k = (
        settings.reranker_prefetch_limit
        if settings.reranking_enabled
        else k
    )

    return AsyncQdrantRetriever(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=embeddings,
        sparse_embedding=sparse_embedding,
        lemmatize=settings.bm25_lemmatize,
        k=effective_k,
        filter=search_filter,
        score_threshold=settings.dense_score_threshold,
    )


def build_retriever_for_document(
    settings: RagServiceSettings,
    document_id: str,
    *,
    qdrant_client: AsyncQdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str = COLLECTION_NAME,
    k: int = 4,
    sparse_embedding=None,
) -> AsyncQdrantRetriever:
    """Build an async retriever scoped to a single document.

    Returns a hybrid ``AsyncQdrantRetriever`` (dense + sparse).
    When ``settings.reranking_enabled``, uses a larger ``k`` equal to
    ``reranker_prefetch_limit`` so the downstream HTTP reranker
    reranker receives enough candidates.
    """
    if qdrant_client is None:
        qdrant_client = build_qdrant_client(settings)
    if embeddings is None:
        embeddings = build_embeddings(settings)

    search_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.document_id",
                match=models.MatchValue(value=document_id),
            )
        ]
    )

    effective_k = (
        settings.reranker_prefetch_limit
        if settings.reranking_enabled
        else k
    )

    return AsyncQdrantRetriever(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=embeddings,
        sparse_embedding=sparse_embedding,
        lemmatize=settings.bm25_lemmatize,
        k=effective_k,
        filter=search_filter,
        score_threshold=settings.dense_score_threshold,
    )
