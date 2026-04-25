"""VK bot factory — creates a Bot instance with all handlers registered."""

from __future__ import annotations

import logging

from vkbottle import Bot, BuiltinStateDispenser

from cafetera_vk_bot.config import VKSettings
from cafetera_vk_bot.handlers import (
    ask,
    fallback,
    fire,
    hire,
    pay,
    sections,
    set_state_dispenser,
    start,
    vacation,
)

logger = logging.getLogger(__name__)

# Order matters: vkbottle checks handlers top-to-bottom.
# 1. start — /start, home (clears dialog state)
# 2. ask — free-text question (state-based, must precede fallback)
# 3. hire / fire / vacation / pay — dedicated clickable flows
# 4. sections — remaining section stubs (sick, probation)
# 5. fallback — must be last — it matches everything
_HANDLER_LABELERS = [
    start.bl,
    ask.bl,
    hire.bl,
    fire.bl,
    vacation.bl,
    pay.bl,
    sections.bl,
    fallback.bl,  # must be last — it matches everything
]


def create_bot(settings: VKSettings) -> Bot:
    """Build a fully-wired vkbottle Bot ready for polling or callback mode."""
    bot = Bot(token=settings.vk_access_token)

    # Create and share state dispenser between bot and handlers
    sd = BuiltinStateDispenser()
    bot.state_dispenser = sd
    set_state_dispenser(sd)

    for labeler in _HANDLER_LABELERS:
        bot.labeler.load(labeler)

    logger.info("VK bot created, %d handler labelers loaded", len(_HANDLER_LABELERS))
    return bot
