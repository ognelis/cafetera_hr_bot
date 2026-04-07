from pydantic_settings import BaseSettings


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
    db_path: str = "data/cafetera.db"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rag-documents"

    # Admin
    admin_api_key: str = ""

    # Indexing concurrency
    max_concurrent_indexing: int = 2

    # Chunking (smaller chunks = faster embedding on local models)
    chunk_size: int = 1000
    chunk_overlap: int = 200
