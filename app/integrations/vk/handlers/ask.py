"""Ask-a-question handler — Block 9.

Flow: CMD_ASK -> set ASK_QUESTION state -> user types text -> RAG answer.

9.1  Free text -> RAG chain -> answer.
     If answer relates to a clickable scenario -> suggest navigation.
     If RAG found nothing -> S-ERR-02 + [Contact HR].
9.2  Background topics (transfer, discipline, absenteeism) ->
     RAG answer + topic-specific disclaimer.

The state is needed so the fallback handler does not swallow the free-text input.
Uses the shared state_dispenser from hr_request module.
"""

from __future__ import annotations

import logging

from vkbottle.bot import BotLabeler, Message

from app.domain.topic_hints import detect_topic_hint
from app.integrations.vk.handlers import get_state_dispenser, query_rag_with_wait
from app.integrations.vk.keyboards import (
    CMD_ASK,
    ask_input_kb,
    ask_result_kb,
)
from app.integrations.vk.states import BotStates

logger = logging.getLogger(__name__)

bl = BotLabeler()


# -- entry point: CMD_ASK -> prompt for free text ---------------------


@bl.message(payload=CMD_ASK)
async def on_ask(message: Message) -> None:
    await get_state_dispenser().set(message.peer_id, BotStates.ASK_QUESTION)
    await message.answer(
        "❓ Задать вопрос\n\n"
        "Напишите ваш вопрос — я постараюсь найти ответ в базе знаний.",
        keyboard=ask_input_kb().get_json(),
    )


# -- state handler: receive free text -> RAG answer -------------------


@bl.message(state=BotStates.ASK_QUESTION)
async def on_ask_text(message: Message) -> None:
    question = message.text.strip()
    if not question:
        await message.answer(
            "Пожалуйста, введите текст вопроса:",
            keyboard=ask_input_kb().get_json(),
        )
        return

    # Clear state before answering
    try:
        await get_state_dispenser().delete(message.peer_id)
    except Exception:
        logger.warning("Failed to clear state for peer %s", message.peer_id, exc_info=True)

    # Show typing indicator while RAG processes
    await message.ctx_api.messages.set_activity(
        type="typing", peer_id=message.peer_id,
    )

    # Detect topic hints (9.1 scenario link, 9.2 disclaimer)
    hint = detect_topic_hint(question)

    # Query the RAG chain with wait message
    answer = await query_rag_with_wait(message, question)

    # Append background-topic disclaimer if detected (9.2)
    if hint.disclaimer:
        answer = f"{answer}\n\n{hint.disclaimer}"

    # Prepend user's question context at the top (truncated if very long)
    question_display = question if len(question) <= 100 else question[:100] + "…"
    answer = f"❓ {question_display}\n\n{answer}"

    await message.answer(
        answer,
        keyboard=ask_result_kb(scenario_id=hint.scenario_id).get_json(),
    )
