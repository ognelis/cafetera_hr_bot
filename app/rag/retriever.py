"""Dense retriever backed by Qdrant vector store."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_qdrant import QdrantVectorStore


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
    from langchain_core.vectorstores import VectorStoreRetriever
    from qdrant_client import QdrantClient

    from app.config import Settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hr_documents"


def build_qdrant_client(settings: Settings) -> QdrantClient:
    """Create a Qdrant client from settings."""
    from qdrant_client import QdrantClient

    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def build_embeddings(settings: Settings) -> Embeddings:
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
        from langchain_ollama import OllamaEmbeddings
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
    client: QdrantClient,
    embeddings: Embeddings,
    collection_name: str = COLLECTION_NAME,
    sparse_embedding=None,
) -> QdrantVectorStore:
    """Wrap an existing Qdrant collection into a LangChain vectorstore."""
    kwargs = dict(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    if sparse_embedding is not None:
        kwargs["sparse_embedding"] = sparse_embedding
    return QdrantVectorStore(**kwargs)


def build_retriever(
    settings: Settings,
    *,
    qdrant_client: QdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str = COLLECTION_NAME,
    k: int = 4,
    sparse_embedding=None,
) -> VectorStoreRetriever:
    """Build a dense retriever over the given Qdrant collection.

    Only chunks where ``is_search_enabled`` is not explicitly ``False``
    are returned.  Chunks that predate the metadata enrichment (no field)
    are still included for backward compatibility.
    """
    from qdrant_client import models

    if qdrant_client is None:
        qdrant_client = build_qdrant_client(settings)
    if embeddings is None:
        embeddings = build_embeddings(settings)

    vs = build_vectorstore(
        qdrant_client,
        embeddings,
        collection_name,
        sparse_embedding=sparse_embedding,
    )
    search_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.is_search_enabled",
                match=models.MatchValue(value=True),
            )
        ]
    )
    return vs.as_retriever(search_kwargs={"k": k, "filter": search_filter})


def build_retriever_for_document(
    settings: Settings,
    document_id: str,
    *,
    qdrant_client: QdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str = COLLECTION_NAME,
    k: int = 4,
    sparse_embedding=None,
) -> VectorStoreRetriever:
    """Build a dense retriever scoped to a single document.

    Returns only chunks that:
    - belong to ``document_id`` (``metadata.document_id`` must match), and
    - are not explicitly excluded from search (``is_search_enabled`` != ``False``).
    """
    from qdrant_client import models

    if qdrant_client is None:
        qdrant_client = build_qdrant_client(settings)
    if embeddings is None:
        embeddings = build_embeddings(settings)

    vs = build_vectorstore(
        qdrant_client,
        embeddings,
        collection_name,
        sparse_embedding=sparse_embedding,
    )
    search_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.document_id",
                match=models.MatchValue(value=document_id),
            ),
            models.FieldCondition(
                key="metadata.is_search_enabled",
                match=models.MatchValue(value=True),
            ),
        ]
    )
    return vs.as_retriever(search_kwargs={"k": k, "filter": search_filter})
