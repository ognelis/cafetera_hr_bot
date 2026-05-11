"""VK bot factory — creates a Bot instance with all handlers registered."""

from __future__ import annotations

import logging
from typing import Any

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


def _stringify_numeric_params(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert int/float values to strings so aiohttp FormData can serialize them.

    aiohttp >=3.13 no longer accepts raw integers in FormData:
    https://github.com/aio-libs/aiohttp/issues/4324
    VK API parameters such as ``random_id=0`` arrive as ints from vkbottle
    internals and must be stringified before reaching the HTTP client.
    """
    if data is None:
        return None
    return {
        k: str(v) if type(v) in (int, float) else v
        for k, v in data.items()
    }


def _patch_bot_http_client(bot: Bot) -> None:
    """Monkey-patch the bot's HTTP client to stringify numeric request params.

    This is applied once at bot creation and covers *all* VK API calls
    (messages, uploaders, polling, etc.) without touching individual handlers.
    """
    client = bot.api.http_client
    methods_to_patch = ("request_text", "request_json", "request_raw", "request_content")

    for method_name in methods_to_patch:
        original = getattr(client, method_name)

        async def _patched(
            url: str,
            method: str = "GET",
            data: dict[str, Any] | None = None,
            *,
            _original: Any = original,
            **kwargs: Any,
        ) -> Any:
            data = _stringify_numeric_params(data)
            return await _original(url, method=method, data=data, **kwargs)

        setattr(client, method_name, _patched)


def create_bot(settings: VKSettings) -> Bot:
    """Build a fully-wired vkbottle Bot ready for polling or callback mode."""
    bot = Bot(token=settings.vk_access_token)

    # Work around aiohttp 3.13+ FormData int-serialization breakage
    _patch_bot_http_client(bot)

    # Create and share state dispenser between bot and handlers
    sd = BuiltinStateDispenser()
    bot.state_dispenser = sd
    set_state_dispenser(sd)

    for labeler in _HANDLER_LABELERS:
        bot.labeler.load(labeler)

    logger.info("VK bot created, %d handler labelers loaded", len(_HANDLER_LABELERS))
    return bot
