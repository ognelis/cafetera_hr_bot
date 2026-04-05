"""Section entry-point handlers — stubs for sections not yet implemented.

Hire, fire, and vacation are now handled by dedicated handler modules
(hire.py, fire.py, vacation.py).  This module keeps stubs for the
remaining sections (Block 4+).
"""

from vkbottle.bot import BotLabeler, Message

from app.integrations.vk.keyboards import (
    CMD_ASK,
    CMD_HOME,
    CMD_PAY,
    CMD_PROBATION,
    CMD_SICK,
    stub_kb,
)

bl = BotLabeler()


def _section_stub(title: str) -> str:
    return (
        f"{title}\n\n"
        "Раздел в разработке.\n"
        "Выберите другой пункт меню или напишите в HR."
    )


@bl.message(payload=CMD_PAY)
async def on_pay(message: Message) -> None:
    await message.answer(
        _section_stub("💰 Оплата и премии"),
        keyboard=stub_kb(back_payload=CMD_HOME).get_json(),
    )


@bl.message(payload=CMD_SICK)
async def on_sick(message: Message) -> None:
    await message.answer(
        _section_stub("🏥 Больничный / ЭЛН"),
        keyboard=stub_kb(back_payload=CMD_HOME).get_json(),
    )


@bl.message(payload=CMD_PROBATION)
async def on_probation(message: Message) -> None:
    await message.answer(
        _section_stub("📝 Испытательный срок"),
        keyboard=stub_kb(back_payload=CMD_HOME).get_json(),
    )


@bl.message(payload=CMD_ASK)
async def on_ask(message: Message) -> None:
    await message.answer(
        _section_stub("❓ Задать вопрос"),
        keyboard=stub_kb(back_payload=CMD_HOME).get_json(),
    )
