"""Section entry-point handlers — RAG-powered.

Pay and Ask are now handled by dedicated handler modules (pay.py, ask.py).
This module keeps RAG handlers for:
- 🏥 Больничный / ЭЛН (S-50, FR-13)
- 📝 Испытательный срок (S-60, FR-15)
"""

from vkbottle.bot import BotLabeler, Message

from cafetera_vk_bot.handlers import send_rag_answer
from cafetera_vk_bot.keyboards import (
    CMD_HOME,
    CMD_PROBATION,
    CMD_SICK,
)

bl = BotLabeler()


# -- S-50: sick leave / ELN -- RAG (FR-13, Block 8) --------------------


@bl.message(payload=CMD_SICK)
async def on_sick(message: Message) -> None:
    await send_rag_answer(
        message, question="Больничный / ЭЛН", back_payload=CMD_HOME, category="sick",
    )


# -- S-60: probation -- RAG (FR-15, Block 8) ---------------------------


@bl.message(payload=CMD_PROBATION)
async def on_probation(message: Message) -> None:
    await send_rag_answer(
        message, question="Испытательный срок", back_payload=CMD_HOME, category="probation",
    )
