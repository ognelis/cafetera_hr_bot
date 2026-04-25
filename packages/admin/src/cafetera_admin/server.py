"""Local development entry-point: HTTP server for document admin UI.

Usage:
    uv run python -m cafetera_admin.server

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
    - BIND_HOST              — bind address (default: 127.0.0.1)
"""

import logging
import os
import sys

from hypercorn.asyncio import serve
from hypercorn.config import Config

from cafetera_admin.config import AdminSettings
from cafetera_admin.main import create_app
from cafetera_core.config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = AdminSettings()

    if not settings.admin_api_key:
        logger.error("ADMIN_API_KEY is not set. Please configure it in .env file.")
        sys.exit(1)

    host = os.environ.get("BIND_HOST", "127.0.0.1")
    port = 8000

    logger.info("Starting admin server on http://%s:%s (HTTP/2 enabled)", host, port)
    logger.info("Admin UI available at: http://%s:%s/documents", host, port)

    # Configure Hypercorn with HTTP/2 support
    config = Config()
    config.bind = [f"{host}:{port}"]
    config.worker_class = "asyncio"
    config.h2_max_concurrent_streams = 100
    
    # Create app
    app = create_app(settings)

    # Run with HTTP/2
    await serve(app, config)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
