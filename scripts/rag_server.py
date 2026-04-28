"""Thin wrapper: delegates to cafetera_rag_service.server.

Usage:
    uv run python scripts/rag_server.py
"""

from cafetera_rag_service.server import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
