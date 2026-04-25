"""Thin wrapper: delegates to cafetera_admin.server.

Usage:
    uv run python scripts/admin_server.py
"""

from cafetera_admin.server import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
