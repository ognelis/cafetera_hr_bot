import logging

from pydantic_settings import BaseSettings


def configure_logging() -> None:
    """Set up project-wide logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    vk_access_token: str = ""
    vk_group_id: int = 0

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

    # Admin
    admin_api_key: str = ""

    # Indexing concurrency
    max_concurrent_indexing: int = 2

    # Chunking (token counts — uses tiktoken for accurate token measurement)
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Chunking strategy: "recursive" (token-based) or "semantic" (embedding similarity)
    chunk_strategy: str = "recursive"  # "recursive" | "semantic"
    semantic_breakpoint_threshold_type: str = "percentile"
    semantic_breakpoint_threshold_amount: float = 95

    # Retrieval mode: "dense" (vector only) or "hybrid" (dense + sparse BM25)
    retrieval_mode: str = "dense"  # "dense" | "hybrid"
    sparse_embedding_model: str = "Qdrant/bm25"
