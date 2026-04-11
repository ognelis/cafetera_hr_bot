"""Hire flow handlers — S-10, S-11 (FR-2, FR-3, FR-4, FR-14).

Flow: CMD_HIRE → entity selection → action menu → content.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.domain.content import (
    hire_checklist,
    hire_contract_text,
    onboarding_checklist,
)
from app.integrations.vk.handlers import (
    catch_entity_error,
    require_entity,
    send_document_or_fallback,
)
from app.integrations.vk.keyboards import (
    CMD_HIRE,
    CMD_HIRE_CHECKLIST,
    CMD_HIRE_CONTRACT,
    CMD_HIRE_ONBOARDING,
    CMD_HOME,
    entity_select_kb,
    hire_actions_kb,
)
from app.integrations.vk.rules import PayloadCmdRule

bl = BotLabeler()

HIRE_ENTITY_CMD = "hire_entity"


# ── S-10: entry → entity selection (NFR-7) ────────────────────────


@bl.message(payload=CMD_HIRE)
async def on_hire(message: Message) -> None:
    await message.answer(
        "👤 Приём сотрудника\n\nВыберите юридическое лицо:",
        keyboard=entity_select_kb(HIRE_ENTITY_CMD, back_payload=CMD_HOME).get_json(),
    )


# ── S-11: entity selected → action menu ───────────────────────────


@bl.message(PayloadCmdRule(HIRE_ENTITY_CMD))
@catch_entity_error
async def on_hire_entity(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = await require_entity(message, entity_id, back_payload=CMD_HOME)
    await message.answer(
        f"👤 Приём сотрудника — {entity.full_name}\n\nВыберите действие:",
        keyboard=hire_actions_kb(entity_id).get_json(),
    )


# ── checklist ──────────────────────────────────────────────────────


@bl.message(PayloadCmdRule(CMD_HIRE_CHECKLIST))
@catch_entity_error
async def on_hire_checklist(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = await require_entity(message, entity_id, back_payload=CMD_HIRE)

    await send_document_or_fallback(
        message,
        category="hire",
        subcategory="hire_checklist",
        entity_id=entity_id,
        fallback_text=hire_checklist(entity),
        back_payload=CMD_HIRE,
    )


# ── contract template ─────────────────────────────────────────────


@bl.message(PayloadCmdRule(CMD_HIRE_CONTRACT))
@catch_entity_error
async def on_hire_contract(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = await require_entity(message, entity_id, back_payload=CMD_HIRE)

    caption = f"📄 Шаблон трудового договора — {entity.full_name}\n"
    await send_document_or_fallback(
        message,
        category="hire",
        subcategory="hire_contract",
        entity_id=entity_id,
        fallback_text=hire_contract_text(entity),
        back_payload=CMD_HIRE,
        caption=caption,
    )


# ── onboarding checklist ──────────────────────────────────────────


@bl.message(PayloadCmdRule(CMD_HIRE_ONBOARDING))
@catch_entity_error
async def on_hire_onboarding(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = await require_entity(message, entity_id, back_payload=CMD_HIRE)

    await send_document_or_fallback(
        message,
        category="hire",
        subcategory="hire_onboarding",
        entity_id=entity_id,
        fallback_text=onboarding_checklist(entity),
        back_payload=CMD_HIRE,
    )
