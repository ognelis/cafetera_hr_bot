"""VK bot factory — creates a Bot instance with all handlers registered."""

from __future__ import annotations

import logging

from vkbottle import Bot

from app.config import Settings
from app.integrations.vk.handlers import fallback, sections, start

logger = logging.getLogger(__name__)

# Order matters: vkbottle checks handlers top-to-bottom.
# The fallback labeler must be loaded last so it only catches unmatched messages.
_HANDLER_LABELERS = [
    start.bl,
    sections.bl,
    fallback.bl,  # must be last — it matches everything
]


def create_bot(settings: Settings) -> Bot:
    """Build a fully-wired vkbottle Bot ready for polling or callback mode."""
    bot = Bot(token=settings.vk_access_token)

    for labeler in _HANDLER_LABELERS:
        bot.labeler.load(labeler)

    logger.info("VK bot created, %d handler labelers loaded", len(_HANDLER_LABELERS))
    return bot
