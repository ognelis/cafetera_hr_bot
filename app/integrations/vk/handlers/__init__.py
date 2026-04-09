"""VK handlers package."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from vkbottle import BuiltinStateDispenser
from vkbottle.bot import Message

from app.domain.qa_service import QAService

logger = logging.getLogger(__name__)


@dataclass
class Holder:
    qa: QAService | None = None
    state_dispenser: BuiltinStateDispenser | None = None


holder = Holder()


def set_qa_service(service: QAService) -> None:
    holder.qa = service


def get_qa_service() -> QAService:
    if holder.qa is None:
        raise RuntimeError("QA service not initialized")
    return holder.qa


def set_state_dispenser(sd: BuiltinStateDispenser) -> None:
    holder.state_dispenser = sd


def get_state_dispenser() -> BuiltinStateDispenser:
    if holder.state_dispenser is None:
        raise RuntimeError("State dispenser not initialized")
    return holder.state_dispenser


async def query_rag_with_wait(
    message: Message,
    question: str,
    *,
    timeout: float = 3.0,
) -> str:
    """Query RAG chain; send a 'please wait' message if it takes longer than *timeout* seconds."""
    rag_task = asyncio.create_task(get_qa_service().ask(question))
    delay_task = asyncio.create_task(asyncio.sleep(timeout))

    done, _ = await asyncio.wait(
        {rag_task, delay_task}, return_when=asyncio.FIRST_COMPLETED,
    )

    if rag_task in done:
        delay_task.cancel()
        logger.debug("RAG answered within timeout for peer %s", message.peer_id)
        return rag_task.result()

    logger.info("RAG slow for peer %s, sending wait message", message.peer_id)
    await message.answer("⏳ Ваш вопрос обрабатывается, подождите до 1 минуты…")
    return await rag_task


async def send_rag_answer(message: Message, question: str, back_payload: str) -> None:
    """Send typing indicator, query RAG, and reply with answer + back keyboard.

    If the RAG chain takes longer than 3 seconds, sends a "please wait"
    notification before delivering the final answer.
    """
    from app.integrations.vk.keyboards import stub_kb

    await message.ctx_api.messages.set_activity(type="typing", peer_id=message.peer_id)
    answer = await query_rag_with_wait(message, question)

    # Prepend topic/question context at the top
    question_display = question if len(question) <= 200 else question[:200] + "…"
    answer = f"💬 {question_display}\n\n{answer}"

    await message.answer(answer, keyboard=stub_kb(back_payload=back_payload).get_json())


async def get_entity_or_error(message: Message, entity_id: int | None, back_payload: str):
    """Look up entity by ID; if not found, send error and return None."""
    from app.domain.entities import ENTITY_BY_ID
    from app.integrations.vk.keyboards import stub_kb

    entity = ENTITY_BY_ID.get(entity_id or 0)
    if entity is None:
        await message.answer(
            "Ошибка. Вернитесь в меню.",
            keyboard=stub_kb(back_payload=back_payload).get_json(),
        )
    return entity
