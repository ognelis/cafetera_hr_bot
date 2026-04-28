"""Run the VK bot in Long Poll mode (local development).

Usage:
    uv run python -m cafetera_vk_bot.polling
"""

from __future__ import annotations

import logging

from cafetera_core.config import configure_logging
from cafetera_core.resources import build_resources, close_resources
from cafetera_vk_bot.bot import create_bot
from cafetera_vk_bot.config import VKSettings
from cafetera_vk_bot.handlers import set_category_file_service, set_rag_client, set_system_prompt
from cafetera_vk_bot.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def _setup(bot) -> None:
    """Initialize resources inside vkbottle's event loop.

    This runs via loop_wrapper.on_startup so all resources (especially the
    DB pool) bind to the same event loop that handlers will use.
    """
    settings = bot._settings
    res = await build_resources(settings, with_s3=True, with_db=True)

    # Store resources on bot for cleanup access
    bot._app_resources = res

    if res.rag_client is not None:
        set_rag_client(res.rag_client)
        set_system_prompt(SYSTEM_PROMPT)
    else:
        logger.warning("RAG client not available — bot will not answer questions")

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
    settings = VKSettings()

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
