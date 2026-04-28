"""Allow ``python -m cafetera_rag_service`` to start the server."""

import asyncio

from cafetera_rag_service.server import main

asyncio.run(main())
