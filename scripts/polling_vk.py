"""Local development entry-point: VK bot in Long Poll mode.

Usage:
    uv run python scripts/polling_vk.py
"""

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


def main() -> None:
    settings = Settings()
    bot = create_bot(settings)
    logger.info("Starting VK bot in Long Poll mode …")
    bot.run_forever()


if __name__ == "__main__":
    main()
