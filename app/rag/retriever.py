"""Dense retriever backed by Qdrant vector store."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_qdrant import QdrantVectorStore

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStoreRetriever
    from qdrant_client import QdrantClient

    from app.config import Settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hr_documents"


def build_embeddings(settings: Settings) -> Embeddings:
    """Create an embedding model based on ``settings.llm_provider``."""
    if settings.llm_provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.llm_api_key,
            openai_api_base=settings.llm_base_url or None,
        )

    if settings.llm_provider == "llamacpp":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.llm_api_key or "no-key",
            openai_api_base=settings.llm_base_url or "http://localhost:8080/v1",
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
        base_url=settings.llm_base_url,
    )


def build_vectorstore(
    client: QdrantClient,
    embeddings: Embeddings,
    collection_name: str = COLLECTION_NAME,
) -> QdrantVectorStore:
    """Wrap an existing Qdrant collection into a LangChain vectorstore."""
    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )


def build_retriever(
    client: QdrantClient,
    embeddings: Embeddings,
    collection_name: str = COLLECTION_NAME,
    *,
    k: int = 4,
) -> VectorStoreRetriever:
    """Build a dense retriever over the given Qdrant collection.

    Only chunks where ``is_search_enabled`` is not explicitly ``False``
    are returned.  Chunks that predate the metadata enrichment (no field)
    are still included for backward compatibility.
    """
    from qdrant_client import models

    vs = build_vectorstore(client, embeddings, collection_name)
    search_filter = models.Filter(
        must_not=[
            models.FieldCondition(
                key="metadata.is_search_enabled",
                match=models.MatchValue(value=False),
            )
        ]
    )
    return vs.as_retriever(search_kwargs={"k": k, "filter": search_filter})
