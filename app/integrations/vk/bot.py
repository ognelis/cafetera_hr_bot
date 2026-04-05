"""VK bot factory — creates a Bot instance with all handlers registered."""

from __future__ import annotations

import logging

from vkbottle import Bot

from app.config import Settings
from app.integrations.vk.handlers import (
    fallback,
    fire,
    hire,
    hr_request,
    sections,
    start,
    vacation,
)

logger = logging.getLogger(__name__)

# Order matters: vkbottle checks handlers top-to-bottom.
# 1. start — /start, home (clears dialog state)
# 2. hr_request — contact_hr entry + back/restart payloads + state handlers
# 3. hire / fire / vacation — dedicated clickable flows
# 4. sections — remaining section stubs
# 5. fallback — must be last — it matches everything
_HANDLER_LABELERS = [
    start.bl,
    hr_request.bl,
    hire.bl,
    fire.bl,
    vacation.bl,
    sections.bl,
    fallback.bl,  # must be last — it matches everything
]


def create_bot(settings: Settings) -> Bot:
    """Build a fully-wired vkbottle Bot ready for polling or callback mode."""
    bot = Bot(token=settings.vk_access_token)

    # Share state dispenser between bot and hr_request handlers
    bot.state_dispenser = hr_request.state_dispenser

    for labeler in _HANDLER_LABELERS:
        bot.labeler.load(labeler)

    logger.info("VK bot created, %d handler labelers loaded", len(_HANDLER_LABELERS))
    return bot
