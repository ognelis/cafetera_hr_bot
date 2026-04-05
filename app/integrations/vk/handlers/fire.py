"""Fire flow handlers — S-20, S-21b (FR-5, FR-6, FR-12).

Flow: CMD_FIRE → fire menu → checklist / bypass sheet / RAG.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.domain import qa_service
from app.domain.content import FIRE_BYPASS_SHEET_TEXT, FIRE_LAST_DAY_CHECKLIST
from app.integrations.vk.keyboards import (
    CMD_FIRE,
    CMD_FIRE_BYPASS,
    CMD_FIRE_CHECKLIST,
    CMD_FIRE_GROUNDS,
    CMD_FIRE_RAG,
    fire_menu_kb,
    stub_kb,
)

bl = BotLabeler()


# ── S-20: entry → fire section menu ───────────────────────────────


@bl.message(payload=CMD_FIRE)
async def on_fire(message: Message) -> None:
    await message.answer(
        "🚪 Увольнение\n\nВыберите действие:",
        keyboard=fire_menu_kb().get_json(),
    )


# ── FR-6: last-day checklist ──────────────────────────────────────


@bl.message(payload=CMD_FIRE_CHECKLIST)
async def on_fire_checklist(message: Message) -> None:
    await message.answer(
        FIRE_LAST_DAY_CHECKLIST,
        keyboard=stub_kb(back_payload=CMD_FIRE).get_json(),
    )


# ── S-21b: bypass sheet ───────────────────────────────────────────


@bl.message(payload=CMD_FIRE_BYPASS)
async def on_fire_bypass(message: Message) -> None:
    await message.answer(
        FIRE_BYPASS_SHEET_TEXT,
        keyboard=stub_kb(back_payload=CMD_FIRE).get_json(),
    )


# ── FR-5: voluntary dismissal — RAG (Block 7) ─────────────────────


@bl.message(payload=CMD_FIRE_RAG)
async def on_fire_rag(message: Message) -> None:
    await message.ctx_api.messages.set_activity(type="typing", peer_id=message.peer_id)
    answer = await qa_service.ask("Увольнение по собственному желанию")
    await message.answer(
        answer,
        keyboard=stub_kb(back_payload=CMD_FIRE).get_json(),
    )


# ── FR-12: dismissal grounds — RAG (Block 8) ──────────────────────


@bl.message(payload=CMD_FIRE_GROUNDS)
async def on_fire_grounds(message: Message) -> None:
    await message.ctx_api.messages.set_activity(type="typing", peer_id=message.peer_id)
    answer = await qa_service.ask("Основания увольнения")
    await message.answer(
        answer,
        keyboard=stub_kb(back_payload=CMD_FIRE).get_json(),
    )
