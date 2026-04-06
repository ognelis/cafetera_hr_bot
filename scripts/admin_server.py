"""Local development entry-point: HTTP server for document admin UI.

Usage:
    uv run python scripts/admin_server.py

Environment variables (see .env.example):
    - ADMIN_API_KEY          — required for admin authentication
    - DB_PATH                — SQLite database path (default: data/cafetera.db)
    - S3_ENDPOINT_URL        — MinIO/S3 endpoint (default: http://localhost:9000)
    - S3_ACCESS_KEY          — S3 access key
    - S3_SECRET_KEY          — S3 secret key
    - S3_BUCKET              — S3 bucket name (default: rag-documents)
    - QDRANT_URL             — Qdrant URL (default: http://localhost:6333)
    - QDRANT_API_KEY         — Qdrant API key (optional)
    - QDRANT_COLLECTION      — Collection name (default: hr_documents)
    - LLM_PROVIDER           — llm provider for embeddings (default: ollama)
    - LLM_BASE_URL           — base URL for embeddings API (default: http://localhost:11434)
    - EMBEDDING_MODEL        — embedding model name (default: nomic-embed-text)
"""

import logging
import sys

# Allow running from project root
sys.path.insert(0, ".")

import uvicorn

from app.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()

    if not settings.admin_api_key:
        logger.error("ADMIN_API_KEY is not set. Please configure it in .env file.")
        sys.exit(1)

    host = "127.0.0.1"
    port = 8000

    logger.info("Starting admin server on http://%s:%s", host, port)
    logger.info("Admin UI available at: http://%s:%s/documents", host, port)

    # Run uvicorn with the FastAPI app factory
    uvicorn.run(
        "app.main:create_app",
        host=host,
        port=port,
        reload=True,
        factory=True,
    )


if __name__ == "__main__":
    main()
