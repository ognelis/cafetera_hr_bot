"""Start, main menu, and home navigation handlers."""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.integrations.vk.keyboards import (
    CMD_HOME,
    main_menu_kb,
)

bl = BotLabeler()

GREETING = (
    "Привет! Я HR-бот Cafetera.\n"
    "Помогу найти документ, инструкцию или ответ на кадровый вопрос.\n\n"
    "Выберите раздел в меню ниже 👇"
)

MAIN_MENU_TEXT = "🏠 Главное меню — выберите раздел:"


async def send_main_menu(message: Message, *, text: str = MAIN_MENU_TEXT) -> None:
    """Send the S-01 main menu to the user."""
    await message.answer(text, keyboard=main_menu_kb().get_json())


# ── /start (first message or «Начать» button) ─────────────────────


@bl.message(text=["/start", "Начать", "начать", "Start", "start"])
async def on_start(message: Message) -> None:
    # Clear any lingering dialog state
    from app.integrations.vk.handlers.hr_request import _clear_state

    await _clear_state(message.peer_id)
    await message.answer(GREETING, keyboard=main_menu_kb().get_json())


# ── 🏠 Home button (payload) ──────────────────────────────────────


@bl.message(payload=CMD_HOME)
async def on_home(message: Message) -> None:
    # Clear any lingering dialog state
    from app.integrations.vk.handlers.hr_request import _clear_state

    await _clear_state(message.peer_id)
    await send_main_menu(message)
