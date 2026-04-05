"""Section entry-point handlers — RAG-powered.

Pay and Ask are now handled by dedicated handler modules (pay.py, ask.py).
This module keeps RAG handlers for:
- 🏥 Больничный / ЭЛН (S-50, FR-13)
- 📝 Испытательный срок (S-60, FR-15)
"""

from vkbottle.bot import BotLabeler, Message

from app.domain import qa_service
from app.integrations.vk.keyboards import (
    CMD_HOME,
    CMD_PROBATION,
    CMD_SICK,
    stub_kb,
)

bl = BotLabeler()


# -- S-50: sick leave / ELN -- RAG (FR-13, Block 8) --------------------


@bl.message(payload=CMD_SICK)
async def on_sick(message: Message) -> None:
    await message.ctx_api.messages.set_activity(type="typing", peer_id=message.peer_id)
    answer = await qa_service.ask("Больничный / ЭЛН")
    await message.answer(
        answer,
        keyboard=stub_kb(back_payload=CMD_HOME).get_json(),
    )


# -- S-60: probation -- RAG (FR-15, Block 8) ---------------------------


@bl.message(payload=CMD_PROBATION)
async def on_probation(message: Message) -> None:
    await message.ctx_api.messages.set_activity(type="typing", peer_id=message.peer_id)
    answer = await qa_service.ask("Испытательный срок")
    await message.answer(
        answer,
        keyboard=stub_kb(back_payload=CMD_HOME).get_json(),
    )
