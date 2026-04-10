"""Fire flow handlers — S-20, S-21b (FR-5, FR-6, FR-12).

Flow: CMD_FIRE → fire menu → checklist / bypass sheet / resignation template.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.domain.content import TEMPLATE_DISCLAIMER
from app.integrations.vk.attachments import send_category_document
from app.integrations.vk.handlers import get_category_file_service, get_entity_or_error, send_rag_answer
from app.integrations.vk.keyboards import (
    CMD_FIRE,
    CMD_FIRE_GROUNDS,
    CMD_FIRE_RESIGNATION,
    FIRE_RESIGNATION_ENTITY_CMD,
    entity_select_kb,
    fire_menu_kb,
    stub_kb,
)
from app.integrations.vk.rules import PayloadCmdRule

bl = BotLabeler()


# ── S-20: entry → fire section menu ───────────────────────────────


@bl.message(payload=CMD_FIRE)
async def on_fire(message: Message) -> None:
    await message.answer(
        "🚪 Увольнение\n\nВыберите действие:",
        keyboard=fire_menu_kb().get_json(),
    )


# ── FR-5: voluntary dismissal — entity selection → template ───────


@bl.message(payload=CMD_FIRE_RESIGNATION)
async def on_fire_resignation(message: Message) -> None:
    await message.answer(
        "🚪 Увольнение по собственному\n\nВыберите юридическое лицо:",
        keyboard=entity_select_kb(FIRE_RESIGNATION_ENTITY_CMD, back_payload=CMD_FIRE).get_json(),
    )


@bl.message(PayloadCmdRule(FIRE_RESIGNATION_ENTITY_CMD))
async def on_fire_resignation_entity(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = await get_entity_or_error(message, entity_id, back_payload=CMD_FIRE)
    if entity is None:
        return

    caption = f"📄 Заявление об увольнении — {entity.full_name}\n\n{TEMPLATE_DISCLAIMER}"
    await send_category_document(
        message,
        get_category_file_service(),
        category="fire",
        subcategory="fire_resignation",
        entity_id=entity_id,
        caption=caption,
    )


# ── FR-12: dismissal grounds — RAG (Block 8) ──────────────────────


@bl.message(payload=CMD_FIRE_GROUNDS)
async def on_fire_grounds(message: Message) -> None:
    await send_rag_answer(message, question="Основания увольнения", back_payload=CMD_FIRE)
