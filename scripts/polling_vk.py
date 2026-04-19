"""Run the VK bot in Long Poll mode (local development).

Usage:
    uv run python scripts/polling_vk.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings, configure_logging
from app.integrations.vk.bot import create_bot
from app.integrations.vk.handlers import set_category_file_service, set_qa_service
from app.resources import build_resources, close_resources

logger = logging.getLogger(__name__)


async def _setup(bot) -> None:
    """Initialize resources inside vkbottle's event loop.

    This runs via loop_wrapper.on_startup so all resources (especially the
    DB pool) bind to the same event loop that handlers will use.
    """
    settings = bot._settings  # type: ignore[attr-defined]
    res = await build_resources(settings, with_s3=True, with_db=True)

    # Store resources on bot for cleanup access
    bot._app_resources = res  # type: ignore[attr-defined]

    if res.vk_qa_service:
        set_qa_service(res.vk_qa_service)
    if res.category_file_service:
        set_category_file_service(res.category_file_service)
    else:
        logger.warning("CategoryFileService not available — document downloads disabled")

    logger.info("Resources initialized successfully")


async def _cleanup(bot) -> None:
    """Close resources on shutdown."""
    res = getattr(bot, "_app_resources", None)
    if res is not None:
        await close_resources(res)
        logger.info("Resources closed")


def main() -> None:
    configure_logging()

    # Initialize settings synchronously (no async needed)
    settings = Settings()

    # Create bot synchronously
    bot = create_bot(settings)
    bot._settings = settings  # type: ignore[attr-defined]

    # Register startup and shutdown handlers in vkbottle's loop_wrapper.
    # on_startup/on_shutdown expect awaitable objects (coroutines), not functions.
    bot.loop_wrapper.on_startup.append(_setup(bot))
    bot.loop_wrapper.on_shutdown.append(_cleanup(bot))

    logger.info("Starting VK bot in Long Poll mode …")
    bot.run_forever()


if __name__ == "__main__":
    main()
