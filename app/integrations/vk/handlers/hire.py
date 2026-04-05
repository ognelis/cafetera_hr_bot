"""Hire flow handlers — S-10, S-11 (FR-2, FR-3, FR-4, FR-14).

Flow: CMD_HIRE → entity selection → action menu → content.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.domain.content import hire_checklist, hire_contract_text, onboarding_checklist
from app.domain.entities import ENTITY_BY_ID
from app.integrations.vk.keyboards import (
    CMD_HIRE,
    CMD_HIRE_CHECKLIST,
    CMD_HIRE_CONTRACT,
    CMD_HIRE_ONBOARDING,
    entity_select_kb,
    hire_actions_kb,
    stub_kb,
)
from app.integrations.vk.rules import PayloadCmdRule

bl = BotLabeler()

HIRE_ENTITY_CMD = "hire_entity"


# ── S-10: entry → entity selection (NFR-7) ────────────────────────


@bl.message(payload=CMD_HIRE)
async def on_hire(message: Message) -> None:
    await message.answer(
        "👤 Приём сотрудника\n\nВыберите юридическое лицо:",
        keyboard=entity_select_kb(HIRE_ENTITY_CMD, back_payload=CMD_HIRE).get_json(),
    )


# ── S-11: entity selected → action menu ───────────────────────────


@bl.message(PayloadCmdRule(HIRE_ENTITY_CMD))
async def on_hire_entity(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = ENTITY_BY_ID.get(entity_id)
    if entity is None:
        await message.answer(
            "Юрлицо не найдено. Попробуйте ещё раз.",
            keyboard=entity_select_kb(HIRE_ENTITY_CMD, back_payload=CMD_HIRE).get_json(),
        )
        return
    await message.answer(
        f"👤 Приём сотрудника — {entity.full_name}\n\nВыберите действие:",
        keyboard=hire_actions_kb(entity_id).get_json(),
    )


# ── checklist ──────────────────────────────────────────────────────


@bl.message(PayloadCmdRule(CMD_HIRE_CHECKLIST))
async def on_hire_checklist(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = ENTITY_BY_ID.get(entity_id)
    err_kb = stub_kb(back_payload=CMD_HIRE).get_json()
    if entity is None:
        await message.answer("Ошибка. Вернитесь в меню.", keyboard=err_kb)
        return
    await message.answer(
        hire_checklist(entity),
        keyboard=stub_kb(back_payload=CMD_HIRE).get_json(),
    )


# ── contract template ─────────────────────────────────────────────


@bl.message(PayloadCmdRule(CMD_HIRE_CONTRACT))
async def on_hire_contract(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = ENTITY_BY_ID.get(entity_id)
    err_kb = stub_kb(back_payload=CMD_HIRE).get_json()
    if entity is None:
        await message.answer("Ошибка. Вернитесь в меню.", keyboard=err_kb)
        return
    await message.answer(
        hire_contract_text(entity),
        keyboard=stub_kb(back_payload=CMD_HIRE).get_json(),
    )


# ── onboarding checklist ──────────────────────────────────────────


@bl.message(PayloadCmdRule(CMD_HIRE_ONBOARDING))
async def on_hire_onboarding(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = ENTITY_BY_ID.get(entity_id)
    err_kb = stub_kb(back_payload=CMD_HIRE).get_json()
    if entity is None:
        await message.answer("Ошибка. Вернитесь в меню.", keyboard=err_kb)
        return
    await message.answer(
        onboarding_checklist(entity),
        keyboard=stub_kb(back_payload=CMD_HIRE).get_json(),
    )
