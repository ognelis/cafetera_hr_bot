"""Fallback handler — catches any unmatched text input."""

from vkbottle.bot import BotLabeler, Message

from cafetera_vk_bot.keyboards import main_menu_kb

bl = BotLabeler()

FALLBACK_TEXT = (
    "В доступных документах нет ответа на этот вопрос.\n"
    "Воспользуйтесь кнопками меню ниже 👇"
)


@bl.message()
async def on_fallback(message: Message) -> None:
    await message.answer(FALLBACK_TEXT, keyboard=main_menu_kb().get_json())
