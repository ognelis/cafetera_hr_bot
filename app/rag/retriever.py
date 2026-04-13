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


class CollectionNotFoundError(Exception):
    """Raised when the target Qdrant collection does not exist yet."""


class AsyncQdrantRetriever(BaseRetriever):
    """Async retriever using Qdrant's AsyncQdrantClient directly.

    Replaces LangChain's QdrantVectorStore for retrieval to enable
    fully async operations without sync client overhead.
    """

    client: AsyncQdrantClient
    collection_name: str
    embeddings: Any
    k: int = 5
    filter: models.Filter | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Retrieve relevant documents asynchronously."""
        query_vector = await self.embeddings.aembed_query(query)
        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
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

    from app.config import Settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hr_documents"


def build_qdrant_client(settings: Settings) -> AsyncQdrantClient:
    """Create an async Qdrant client from settings."""
    return AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def build_embeddings(settings: Settings) -> Embeddings:
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


def build_sparse_embeddings(settings: Settings):
    """Build sparse embeddings for hybrid search. Returns None if mode is dense."""
    if settings.retrieval_mode != "hybrid":
        return None
    try:
        from langchain_qdrant import FastEmbedSparse
    except ImportError as exc:
        raise ImportError(
            "Install the 'hybrid' extra: uv sync --extra hybrid"
        ) from exc
    try:
        return FastEmbedSparse(model_name=settings.sparse_embedding_model)
    except (ImportError, ValueError) as exc:
        raise ImportError(
            "Install the 'hybrid' extra: uv sync --extra hybrid"
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
    settings: Settings,
    *,
    qdrant_client: AsyncQdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str = COLLECTION_NAME,
    k: int = 4,
    sparse_embedding=None,
) -> AsyncQdrantRetriever:
    """Build an async dense retriever over the given Qdrant collection.

    Only chunks where ``is_search_enabled`` is not explicitly ``False``
    are returned.  Chunks that predate the metadata enrichment (no field)
    are still included for backward compatibility.

    Note: sparse_embedding is accepted for API compatibility but is not
    used by AsyncQdrantRetriever (dense retrieval only).
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
    return AsyncQdrantRetriever(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=embeddings,
        k=k,
        filter=search_filter,
    )


def build_retriever_for_document(
    settings: Settings,
    document_id: str,
    *,
    qdrant_client: AsyncQdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str = COLLECTION_NAME,
    k: int = 4,
    sparse_embedding=None,
) -> AsyncQdrantRetriever:
    """Build an async dense retriever scoped to a single document.

    Returns only chunks that belong to ``document_id``
    (``metadata.document_id`` must match).

    Note: sparse_embedding is accepted for API compatibility but is not
    used by AsyncQdrantRetriever (dense retrieval only).
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
    return AsyncQdrantRetriever(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=embeddings,
        k=k,
        filter=search_filter,
    )
