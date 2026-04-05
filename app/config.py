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
    llm_provider: str = "ollama"  # "ollama" | "openai"
    llm_model: str = "qwen3.5:4b-q4_K_M"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""

    # Embeddings
    embedding_model: str = "nomic-embed-text"
