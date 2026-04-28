"""HTTP server entry-point for the RAG microservice.

Usage:
    uv run python -m cafetera_rag_service
    uv run python packages/rag_service/src/cafetera_rag_service/server.py
"""

import logging
import os

from hypercorn.asyncio import serve
from hypercorn.config import Config

from cafetera_rag_service.main import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    host = os.environ.get("BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("RAG_SERVICE_PORT", "8001"))

    logger.info("Starting RAG service on http://%s:%s (HTTP/2 enabled)", host, port)

    config = Config()
    config.bind = [f"{host}:{port}"]
    config.worker_class = "asyncio"
    config.h2_max_concurrent_streams = 100

    app = create_app()

    await serve(app, config)  # type: ignore[arg-type]


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
