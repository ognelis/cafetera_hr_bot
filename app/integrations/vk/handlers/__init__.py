"""VK handlers package."""

from __future__ import annotations

from vkbottle import BuiltinStateDispenser
from vkbottle.bot import Message

from app.domain.qa_service import QAService

_qa: QAService | None = None

_state_dispenser: BuiltinStateDispenser | None = None


def set_qa_service(service: QAService) -> None:
    global _qa
    _qa = service


def get_qa_service() -> QAService:
    if _qa is None:
        raise RuntimeError("QA service not initialized")
    return _qa


def set_state_dispenser(sd: BuiltinStateDispenser) -> None:
    global _state_dispenser
    _state_dispenser = sd


def get_state_dispenser() -> BuiltinStateDispenser:
    if _state_dispenser is None:
        raise RuntimeError("State dispenser not initialized")
    return _state_dispenser


async def send_rag_answer(message: Message, question: str, back_payload: str) -> None:
    """Send typing indicator, query RAG, and reply with answer + back keyboard."""
    from app.integrations.vk.keyboards import stub_kb

    await message.ctx_api.messages.set_activity(type="typing", peer_id=message.peer_id)
    answer = await get_qa_service().ask(question)
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
