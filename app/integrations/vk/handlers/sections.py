"""Section entry-point handlers — remaining RAG stubs.

Pay and Ask are now handled by dedicated handler modules (pay.py, ask.py).
This module keeps RAG-stub handlers for:
- 🏥 Больничный / ЭЛН (S-50, FR-13)
- 📝 Испытательный срок (S-60, FR-15)
"""

from vkbottle.bot import BotLabeler, Message

from app.domain.content import rag_stub
from app.integrations.vk.keyboards import (
    CMD_HOME,
    CMD_PROBATION,
    CMD_SICK,
    stub_kb,
)

bl = BotLabeler()


# -- S-50: sick leave / ELN -- RAG stub (FR-13) -----------------------


@bl.message(payload=CMD_SICK)
async def on_sick(message: Message) -> None:
    await message.answer(
        rag_stub("Больничный / ЭЛН"),
        keyboard=stub_kb(back_payload=CMD_HOME).get_json(),
    )


# -- S-60: probation -- RAG stub (FR-15) ------------------------------


@bl.message(payload=CMD_PROBATION)
async def on_probation(message: Message) -> None:
    await message.answer(
        rag_stub("Испытательный срок"),
        keyboard=stub_kb(back_payload=CMD_HOME).get_json(),
    )
