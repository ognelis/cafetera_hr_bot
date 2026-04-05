"""Ask-a-question handler — Block 4, section 4.4.

Flow: CMD_ASK -> set ASK_QUESTION state -> user types text -> RAG stub answer.
The state is needed so the fallback handler does not swallow the free-text input.
Uses the shared state_dispenser from hr_request module.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.domain.content import rag_stub
from app.integrations.vk.keyboards import (
    CMD_ASK,
    ask_input_kb,
    stub_kb,
)
from app.integrations.vk.states import BotStates

bl = BotLabeler()


# -- entry point: CMD_ASK -> prompt for free text ---------------------


@bl.message(payload=CMD_ASK)
async def on_ask(message: Message) -> None:
    from app.integrations.vk.handlers.hr_request import state_dispenser

    await state_dispenser.set(message.peer_id, BotStates.ASK_QUESTION)
    await message.answer(
        "❓ Задать вопрос\n\n"
        "Напишите ваш вопрос — я постараюсь найти ответ в базе знаний.",
        keyboard=ask_input_kb().get_json(),
    )


# -- state handler: receive free text -> RAG stub ---------------------


@bl.message(state=BotStates.ASK_QUESTION)
async def on_ask_text(message: Message) -> None:
    from app.integrations.vk.handlers.hr_request import state_dispenser

    question = message.text.strip()
    if not question:
        await message.answer(
            "Пожалуйста, введите текст вопроса:",
            keyboard=ask_input_kb().get_json(),
        )
        return

    # Clear state before answering
    try:
        await state_dispenser.delete(message.peer_id)
    except Exception:
        pass

    await message.answer(
        rag_stub(question),
        keyboard=stub_kb(back_payload=CMD_ASK).get_json(),
    )
