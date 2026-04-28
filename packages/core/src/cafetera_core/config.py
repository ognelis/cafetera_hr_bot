import logging

from pydantic_settings import BaseSettings


def configure_logging() -> None:
    """Set up project-wide logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )


class CoreSettings(BaseSettings):
    """Shared settings for the Cafetera HR Bot core package.

    Contains only settings shared across all packages (storage, RAG service URL, etc.).
    App-specific settings (VK, admin) live in their respective packages.
    """

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # RAG service
    rag_service_url: str = "http://localhost:8001"
    rag_service_api_key: str = ""

    # Storage
    database_url: str = "postgresql://cafetera:cafetera@localhost:5432/cafetera"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rag-documents"

    # Indexing concurrency
    max_concurrent_indexing: int = 2


# Backward compatibility alias — will be removed after full migration
Settings = CoreSettings
