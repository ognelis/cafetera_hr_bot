"""VK handlers package."""

from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
from dataclasses import dataclass

from vkbottle import BuiltinStateDispenser
from vkbottle.bot import Message
from vkbottle.tools import Format

from cafetera_core.domain.category_file_service import CategoryFileService
from cafetera_core.rag_client import RAGClient
from cafetera_vk_bot.formatting import markdown_to_format

logger = logging.getLogger(__name__)


@dataclass
class Holder:
    rag_client: RAGClient | None = None
    system_prompt: str = ""
    state_dispenser: BuiltinStateDispenser | None = None
    category_file_service: CategoryFileService | None = None


holder = Holder()


def set_rag_client(client: RAGClient) -> None:
    holder.rag_client = client


def get_rag_client() -> RAGClient:
    if holder.rag_client is None:
        raise RuntimeError("RAG client not initialized")
    return holder.rag_client


def set_system_prompt(prompt: str) -> None:
    holder.system_prompt = prompt


def get_system_prompt() -> str:
    return holder.system_prompt


def set_category_file_service(service: CategoryFileService) -> None:
    holder.category_file_service = service


def get_category_file_service() -> CategoryFileService | None:
    return holder.category_file_service


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
    category: str | None = None,
) -> str | Format:
    """Query RAG chain; send a 'please wait' message if it takes longer than *timeout* seconds."""
    rag_task = asyncio.create_task(
        get_rag_client().ask(
            question,
            system_prompt=get_system_prompt(),
            category=category,
            include_metadata=True,
        )
    )
    delay_task = asyncio.create_task(asyncio.sleep(timeout))

    try:
        done, _ = await asyncio.wait(
            {rag_task, delay_task}, return_when=asyncio.FIRST_COMPLETED,
        )

        if rag_task in done:
            logger.debug("RAG answered within timeout for peer %s", message.peer_id)
            return markdown_to_format(rag_task.result())

        logger.info("RAG slow for peer %s, sending wait message", message.peer_id)
        await message.answer("⏳ Ваш вопрос обрабатывается, подождите до 1 минуты…")
        return markdown_to_format(await rag_task)
    except Exception:
        logger.exception("RAG query failed for peer %s", message.peer_id)
        raise
    finally:
        delay_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await delay_task


async def send_rag_answer(
    message: Message, question: str, back_payload: dict[str, str],
    *, category: str | None = None,
) -> None:
    """Send typing indicator, query RAG with wait message, and reply with answer + back keyboard."""
    from cafetera_vk_bot.keyboards import stub_kb

    await message.ctx_api.messages.set_activity(type="typing", peer_id=message.peer_id)
    answer = await query_rag_with_wait(message, question, category=category)
    await message.answer(answer, keyboard=stub_kb(back_payload=back_payload).get_json())


class EntityNotFoundError(Exception):
    """Raised by *require_entity* when the entity look-up fails.

    The error message is already sent to the user before the exception
    is raised, so callers only need to abort the handler.
    """


def catch_entity_error(handler):
    """Decorator: silently return if the handler raises *EntityNotFoundError*."""

    @functools.wraps(handler)
    async def wrapper(*args, **kwargs):
        try:
            return await handler(*args, **kwargs)
        except EntityNotFoundError:
            return

    return wrapper


async def get_entity_or_error(
    message: Message, entity_id: int | None, back_payload: dict[str, str]
):
    """Look up entity by ID; if not found, send error and return None."""
    from cafetera_vk_bot.domain.entities import ENTITY_BY_ID
    from cafetera_vk_bot.keyboards import stub_kb

    entity = ENTITY_BY_ID.get(entity_id or 0)
    if entity is None:
        await message.answer(
            "Ошибка. Вернитесь в меню.",
            keyboard=stub_kb(back_payload=back_payload).get_json(),
        )
    return entity


async def require_entity(message: Message, entity_id: int | None, back_payload: dict[str, str]):
    """Look up entity by ID; raise *EntityNotFoundError* if not found.

    Sends the error message to the user before raising.
    """
    entity = await get_entity_or_error(message, entity_id, back_payload=back_payload)
    if entity is None:
        raise EntityNotFoundError
    return entity


async def send_document_or_fallback(
    message: Message,
    *,
    category: str,
    subcategory: str,
    entity_id: int,
    fallback_text: str | Format,
    back_payload: dict[str, str],
    caption: str | Format | None = None,
) -> None:
    """Try to send a category document; fall back to *fallback_text* with a back button."""
    from cafetera_vk_bot.attachments import send_category_document
    from cafetera_vk_bot.keyboards import stub_kb

    sent = await send_category_document(
        message,
        get_category_file_service(),
        category=category,
        subcategory=subcategory,
        entity_id=entity_id,
        caption=caption,
    )
    if not sent:
        await message.answer(
            fallback_text,
            keyboard=stub_kb(back_payload=back_payload).get_json(),
        )
