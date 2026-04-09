"""Run the VK bot in Long Poll mode (local development).

Usage:
    uv run python scripts/polling_vk.py
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings, configure_logging
from app.integrations.vk.bot import create_bot
from app.integrations.vk.handlers import set_qa_service
from app.resources import AppResources, build_resources, close_resources

logger = logging.getLogger(__name__)


async def _init() -> AppResources:
    settings = Settings()
    return await build_resources(settings)


def main() -> None:
    configure_logging()
    res = asyncio.run(_init())
    bot = create_bot(res.settings)
    if res.vk_qa_service:
        set_qa_service(res.vk_qa_service)
    atexit.register(lambda: asyncio.run(close_resources(res)))

    logger.info("Starting VK bot in Long Poll mode …")
    bot.run_forever()


if __name__ == "__main__":
    main()
