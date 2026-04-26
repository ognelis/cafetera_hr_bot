import logging
from typing import Any

from pydantic_settings import BaseSettings


def configure_logging() -> None:
    """Set up project-wide logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )


class CoreSettings(BaseSettings):
    """Shared settings for the Cafetera HR Bot core package.

    Contains only settings shared across all packages (RAG, storage, etc.).
    App-specific settings (VK, admin) live in their respective packages.
    """

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # RAG / Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "hr_documents"

    # LLM
    llm_provider: str = "ollama"  # "ollama" | "openai" | "llamacpp"
    llm_model: str = "qwen3.5:4b-q4_K_M"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""

    # Embeddings
    embedding_provider: str = "ollama"
    embedding_model: str = "qwen3-embedding:4b-q4_K_M"
    embedding_base_url: str = "http://localhost:11434"
    embedding_api_key: str = ""

    # Storage
    database_url: str = "postgresql://cafetera:cafetera@localhost:5432/cafetera"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rag-documents"

    # Indexing concurrency
    max_concurrent_indexing: int = 2

    # Chunking (token counts — uses tiktoken for accurate token measurement)
    chunk_size: int = 500

    # Tokenizer model for HybridChunker (HuggingFace model name)
    chunker_tokenizer_model: str = "Qwen/Qwen3-Embedding-0.6B"

    # Hybrid search (sparse BM25 embeddings)
    sparse_embedding_model: str = "Qdrant/bm25"

    # Reranking
    reranking_enabled: bool = False
    colbert_rerank_model: str = "colbert-ir/colbertv2.0"
    colbert_prefetch_limit: int = 20
    colbert_rerank_limit: int = 10


# Backward compatibility alias — will be removed after full migration
Settings = CoreSettings


def build_indexing_config(settings: CoreSettings) -> dict[str, Any]:
    """Extract RAG-relevant config fields into a plain dict for per-document storage.

    This snapshot is stored alongside each document so that staleness can be
    detected when any of these parameters change.
    """
    return {
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunker_tokenizer_model": settings.chunker_tokenizer_model,
        "sparse_embedding_model": settings.sparse_embedding_model,
        "reranking_enabled": settings.reranking_enabled,
        "colbert_rerank_model": settings.colbert_rerank_model,
    }


def is_config_stale(stored: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    """Return ``True`` if the stored indexing config differs from *current* or is missing."""
    if stored is None:
        return True
    return stored != current
