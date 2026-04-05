"""Vacation flow handlers — S-30 partial (FR-7, FR-8).

Flow: CMD_VACATION → vacation menu → entity selection → disclaimer + template.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.domain.content import vacation_template_text
from app.domain.entities import ENTITY_BY_ID
from app.integrations.vk.keyboards import (
    CMD_VACATION,
    CMD_VACATION_RAG,
    CMD_VACATION_SELECT,
    CMD_VACATION_TEMPLATE,
    entity_select_kb,
    stub_kb,
    vacation_menu_kb,
)
from app.integrations.vk.rules import PayloadCmdRule

bl = BotLabeler()

_RAG_STUB = (
    "🏖 Порядок оформления отпуска\n\n"
    "Раздел в разработке.\n"
    "Выберите другой пункт меню или напишите в HR."
)


# ── S-30: entry → vacation menu ────────────────────────────────────


@bl.message(payload=CMD_VACATION)
async def on_vacation(message: Message) -> None:
    await message.answer(
        "🏖 Отпуск\n\nВыберите действие:",
        keyboard=vacation_menu_kb().get_json(),
    )


# ── FR-8: select entity for leave application template ─────────────


@bl.message(payload=CMD_VACATION_SELECT)
async def on_vacation_select(message: Message) -> None:
    await message.answer(
        "📄 Заявление на отпуск\n\nВыберите юридическое лицо:",
        keyboard=entity_select_kb(CMD_VACATION_TEMPLATE, back_payload=CMD_VACATION).get_json(),
    )


# ── entity selected → disclaimer + file stub ──────────────────────


@bl.message(PayloadCmdRule(CMD_VACATION_TEMPLATE))
async def on_vacation_template(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = ENTITY_BY_ID.get(entity_id)
    if entity is None:
        await message.answer(
            "Юрлицо не найдено. Попробуйте ещё раз.",
            keyboard=entity_select_kb(CMD_VACATION_TEMPLATE, back_payload=CMD_VACATION).get_json(),
        )
        return
    await message.answer(
        vacation_template_text(entity),
        keyboard=stub_kb(back_payload=CMD_VACATION).get_json(),
    )


# ── FR-7: leave procedure — RAG stub (Block 3) ────────────────────


@bl.message(payload=CMD_VACATION_RAG)
async def on_vacation_rag(message: Message) -> None:
    await message.answer(
        _RAG_STUB,
        keyboard=stub_kb(back_payload=CMD_VACATION).get_json(),
    )
