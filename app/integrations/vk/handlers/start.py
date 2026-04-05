"""Start, main menu, and home navigation handlers."""

from vkbottle.bot import BotLabeler, Message

from app.integrations.vk.keyboards import (
    CMD_CONTACT_HR,
    CMD_HOME,
    main_menu_kb,
    stub_kb,
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
    await message.answer(GREETING, keyboard=main_menu_kb().get_json())


# ── 🏠 Home button (payload) ──────────────────────────────────────


@bl.message(payload=CMD_HOME)
async def on_home(message: Message) -> None:
    await send_main_menu(message)


# ── 💬 Contact HR placeholder ─────────────────────────────────────


@bl.message(payload=CMD_CONTACT_HR)
async def on_contact_hr(message: Message) -> None:
    text = (
        "💬 Написать в HR\n\n"
        "Этот раздел позволит сформировать обращение в HR-отдел.\n"
        "Функция в разработке — скоро здесь появится пошаговый диалог."
    )
    await message.answer(text, keyboard=stub_kb().get_json())
