"""RAG service settings — standalone configuration for the RAG microservice."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class RagServiceSettings(BaseSettings):
    """Configuration for the RAG microservice.

    Standalone settings (does NOT extend CoreSettings) so the service
    can be deployed independently.  Field names match CoreSettings
    for easy sharing of ``.env`` files.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # RAG / Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "hr_documents"
    qdrant_timeout: float = 300.0
    qdrant_upsert_batch_size: int = 32

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "qwen3.5:4b-q4_K_M"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""

    # LLM sampling parameters.
    # Defaults preserve prior behavior (only ``temperature`` is forwarded).
    # Unset (None) fields are NOT passed to the backend, so it keeps its own
    # defaults. Set these in ``.env`` to follow a model's recommendations, e.g.
    # for T-lite-it-2.1: LLM_TEMPERATURE=0.7 LLM_TOP_P=0.8 LLM_TOP_K=20
    # LLM_PRESENCE_PENALTY=1.0
    llm_temperature: float = 0.3
    llm_num_ctx: int = 8192
    llm_max_tokens: int = 8192
    llm_top_p: float | None = None
    llm_top_k: int | None = None
    llm_presence_penalty: float | None = None

    # Disable thinking/reasoning mode for Qwen3/Qwen3.5 models (Ollama and llamacpp)
    llm_disable_thinking: bool = True

    # Embeddings
    embedding_provider: str = "ollama"
    embedding_model: str = "qwen3-embedding:4b-q4_K_M"
    embedding_base_url: str = "http://localhost:11434"
    embedding_api_key: str = ""
    embedding_chunk_size: int = 16

    # Asymmetric query-side instruction (Qwen3 / E5-instruct family).
    # Leave empty to disable (e.g. for BGE-M3 or symmetric models).
    # Format applied to queries only: "Instruct: {task}\nQuery: {text}"
    embedding_query_instruction: str = (
        "Given a web search query, retrieve relevant passages that answer the query"
    )
    embedding_use_query_instruction: bool = True

    # Hybrid search (sparse BM25 embeddings)
    sparse_embedding_model: str = "Qdrant/bm25"
    bm25_lemmatize: bool = True

    # Retrieval k defaults
    doc_query_k: int = 15
    global_max_k: int = 10
    dense_score_threshold: float = 0.0

    # Reranking
    reranking_enabled: bool = False
    reranker_url: str = "http://localhost:8082"
    reranker_model: str = ""
    reranker_top_n: int = 5
    reranker_prefetch_limit: int = 20
    reranker_timeout: float = 30.0

    # Chunking / parsing
    chunk_size: int = 512
    chunker_tokenizer_model: str = "Qwen/Qwen3-Embedding-0.6B"

    # S3 / MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rag-documents"

    # API authentication
    rag_service_api_key: str = ""
