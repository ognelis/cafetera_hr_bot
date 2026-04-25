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
from langchain_qdrant import QdrantVectorStore
from pydantic import ConfigDict
from qdrant_client import AsyncQdrantClient, models


def _to_list(value) -> list:
    """Convert numpy array or passthrough plain list to Python list."""
    return value.tolist() if hasattr(value, "tolist") else value


class CollectionNotFoundError(Exception):
    """Raised when the target Qdrant collection does not exist yet."""


class AsyncHybridRerankRetriever(BaseRetriever):
    """Async retriever using dense + sparse prefetch with ColBERT reranking.

    Uses Qdrant's ``query_points`` with ``prefetch`` for parallel dense
    and sparse retrieval, then reranks candidates via ColBERT late
    interaction (multivector similarity).
    """

    client: AsyncQdrantClient
    collection_name: str
    embeddings: Any
    sparse_embedding: Any
    colbert_embedding: Any
    k: int = 5
    prefetch_limit: int = 20
    filter: models.Filter | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Retrieve and rerank documents using hybrid + ColBERT."""
        from qdrant_client.models import Prefetch, SparseVector

        # 1. Compute dense embedding
        dense_vec = await self.embeddings.aembed_query(query)

        # 2. Compute sparse embedding
        sparse_result = self.sparse_embedding.embed_query(query)
        sparse_vec = SparseVector(
            indices=_to_list(sparse_result.indices),
            values=_to_list(sparse_result.values),
        )

        # 3. Compute ColBERT query embedding
        colbert_vec = self.colbert_embedding.embed_query(query)

        # 4. Build prefetch list and execute rerank query
        prefetch = [
            Prefetch(query=dense_vec, using="dense", limit=self.prefetch_limit),
            Prefetch(query=sparse_vec, using="bm25", limit=self.prefetch_limit),
        ]

        results = await self.client.query_points(
            collection_name=self.collection_name,
            prefetch=prefetch,
            query=colbert_vec,
            using="colbert",
            limit=self.k,
            query_filter=self.filter,
            with_payload=True,
        )

        # 5. Convert to LangChain Documents
        docs: list[Document] = []
        for r in results.points:
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
    k: int = 5
    prefetch_limit: int = 20
    filter: models.Filter | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Retrieve relevant documents asynchronously."""
        query_vector = await self.embeddings.aembed_query(query)

        if self.sparse_embedding is not None:
            # Hybrid search: dense + BM25 prefetch, fused by RRF
            from qdrant_client.models import Prefetch, Rrf, RrfQuery, SparseVector

            sparse_result = self.sparse_embedding.embed_query(query)
            sparse_vec = SparseVector(
                indices=_to_list(sparse_result.indices),
                values=_to_list(sparse_result.values),
            )
            prefetch = [
                Prefetch(query=query_vector, using="dense", limit=self.prefetch_limit),
                Prefetch(query=sparse_vec, using="bm25", limit=self.prefetch_limit),
            ]
            results = await self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query=RrfQuery(rrf=Rrf()),
                limit=self.k,
                query_filter=self.filter,
            )
        else:
            # Dense-only search
            results = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                limit=self.k,
                query_filter=self.filter,
            )

        docs: list[Document] = []
        for r in results.points:
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


def estimate_k(question: str) -> int:
    """Estimate the number of chunks to retrieve based on question complexity.

    Rules:
    - Short questions (≤5 words): k=2
    - Medium questions (6-15 words): k=4 (default)
    - Long/complex questions (>15 words): k=6
    """
    word_count = len(question.split())
    if word_count <= 5:
        return 2
    elif word_count <= 15:
        return 4
    return 6

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

    from cafetera_core.config import CoreSettings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hr_documents"


def build_qdrant_client(settings: CoreSettings) -> AsyncQdrantClient:
    """Create an async Qdrant client from settings."""
    return AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def build_embeddings(settings: CoreSettings) -> Embeddings:
    """Create an embedding model based on ``settings.embedding_provider``."""
    if settings.embedding_provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.embedding_api_key,
            openai_api_base=settings.embedding_base_url or None,
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
            openai_api_key=settings.embedding_api_key or "no-key",
            openai_api_base=settings.embedding_base_url or "http://localhost:8080/v1",
        )

    # Default: Ollama
    try:
        from langchain_ollama import OllamaEmbeddings  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "Install the 'ollama' extra: uv sync --extra ollama"
        ) from exc
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
    )


def build_sparse_embeddings(settings: CoreSettings):
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


def build_vectorstore(
    client: AsyncQdrantClient,
    embeddings: Embeddings,
    collection_name: str = COLLECTION_NAME,
    sparse_embedding=None,
) -> QdrantVectorStore:
    """Wrap an existing Qdrant collection into a LangChain vectorstore.

    Note: This function is primarily used for indexing/ingestion.
    For retrieval, use AsyncQdrantRetriever instead.
    """
    from qdrant_client.http.exceptions import UnexpectedResponse

    # Pre-check: does the collection exist?
    # Note: client is expected to have get_collection method (sync or mock)
    try:
        client.get_collection(collection_name)  # type: ignore[unused-coroutine]
    except (UnexpectedResponse, Exception) as exc:
        raise CollectionNotFoundError(
            f"Qdrant collection '{collection_name}' does not exist yet. "
            f"Upload and index a document first."
        ) from exc

    if sparse_embedding is not None:
        return QdrantVectorStore(
            client=client,  # type: ignore[arg-type]
            collection_name=collection_name,
            embedding=embeddings,
            sparse_embedding=sparse_embedding,
        )
    return QdrantVectorStore(
        client=client,  # type: ignore[arg-type]
        collection_name=collection_name,
        embedding=embeddings,
    )


def build_retriever(
    settings: CoreSettings,
    *,
    qdrant_client: AsyncQdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str = COLLECTION_NAME,
    k: int = 4,
    sparse_embedding=None,
    colbert_embedding=None,
) -> AsyncQdrantRetriever | AsyncHybridRerankRetriever:
    """Build an async retriever over the given Qdrant collection.

    When ``settings.reranking_enabled`` and ``colbert_embedding`` is
    provided, returns an ``AsyncHybridRerankRetriever`` that performs
    dense + sparse prefetch with ColBERT reranking.

    Otherwise returns a hybrid ``AsyncQdrantRetriever`` (dense + sparse).

    Only chunks where ``is_search_enabled`` is not explicitly ``False``
    are returned.  Chunks that predate the metadata enrichment (no field)
    are still included for backward compatibility.
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

    # Dispatch to hybrid reranker when reranking is enabled
    if settings.reranking_enabled and colbert_embedding is not None:
        return AsyncHybridRerankRetriever(
            client=qdrant_client,
            collection_name=collection_name,
            embeddings=embeddings,
            sparse_embedding=sparse_embedding,
            colbert_embedding=colbert_embedding,
            k=k,
            prefetch_limit=settings.colbert_prefetch_limit,
            filter=search_filter,
        )

    return AsyncQdrantRetriever(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=embeddings,
        sparse_embedding=sparse_embedding,
        k=k,
        filter=search_filter,
    )


def build_retriever_for_document(
    settings: CoreSettings,
    document_id: str,
    *,
    qdrant_client: AsyncQdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str = COLLECTION_NAME,
    k: int = 4,
    sparse_embedding=None,
    colbert_embedding=None,
) -> AsyncQdrantRetriever | AsyncHybridRerankRetriever:
    """Build an async retriever scoped to a single document.

    When ``settings.reranking_enabled`` and ``colbert_embedding`` is
    provided, returns an ``AsyncHybridRerankRetriever`` that performs
    dense + sparse prefetch with ColBERT reranking.

    Otherwise returns a hybrid ``AsyncQdrantRetriever`` (dense + sparse).

    Returns only chunks that belong to ``document_id``
    (``metadata.document_id`` must match).
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

    # Dispatch to hybrid reranker when reranking is enabled
    if settings.reranking_enabled and colbert_embedding is not None:
        return AsyncHybridRerankRetriever(
            client=qdrant_client,
            collection_name=collection_name,
            embeddings=embeddings,
            sparse_embedding=sparse_embedding,
            colbert_embedding=colbert_embedding,
            k=k,
            prefetch_limit=settings.colbert_prefetch_limit,
            filter=search_filter,
        )

    return AsyncQdrantRetriever(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=embeddings,
        sparse_embedding=sparse_embedding,
        k=k,
        filter=search_filter,
    )
