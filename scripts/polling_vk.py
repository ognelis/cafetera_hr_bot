"""Local development entry-point: VK bot in Long Poll mode.

Usage:
    uv run python scripts/polling_vk.py
"""

import asyncio
import logging
import sys

# Allow running from project root
sys.path.insert(0, ".")

from app.config import Settings
from app.integrations.vk.bot import create_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = Settings()
    bot = create_bot(settings)
    logger.info("Starting VK bot in Long Poll mode …")
    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
