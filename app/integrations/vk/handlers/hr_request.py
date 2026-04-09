"""HR-request multi-step dialog — S-70 (FR-16, FR-18).

6-step form: name → topic → details → entity → urgency → confirm.
Uses vkbottle state_dispenser for FSM and per-user context storage.
"""

from __future__ import annotations

import logging

from vkbottle.bot import BotLabeler, Message

from app.domain.content import (
    HR_REQUEST_TOPICS,
    HR_REQUEST_URGENCY_OPTIONS,
    format_hr_request,
)
from app.domain.entities import ENTITIES, ENTITY_BY_ID
from app.integrations.vk.handlers import get_state_dispenser
from app.integrations.vk.keyboards import (
    CMD_CONTACT_HR,
    CMD_HOME,
    CMD_HR_BACK,
    CMD_HR_CONFIRM,
    CMD_HR_RESTART,
    hr_confirm_kb,
    hr_done_kb,
    hr_entity_kb,
    hr_topic_kb,
    hr_urgency_kb,
    main_menu_kb,
)
from app.integrations.vk.rules import PayloadCmdRule
from app.integrations.vk.states import BotStates

logger = logging.getLogger(__name__)

bl = BotLabeler()

_ENTITY_SHORT_NAMES = {e.short_name for e in ENTITIES}
_ENTITY_BY_SHORT = {e.short_name: e for e in ENTITIES}


# ── helpers ────────────────────────────────────────────────────────


def _name_input_kb() -> str:
    """Keyboard JSON for the name-input step (only Home + cancel)."""
    from vkbottle import Keyboard, Text

    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🏠 Главное меню", payload=CMD_HOME))
    return kb.get_json()


async def _clear_state(peer_id: int) -> None:
    try:
        await get_state_dispenser().delete(peer_id)
    except Exception:
        pass


# ── entry point: CMD_CONTACT_HR ────────────────────────────────────


@bl.message(payload=CMD_CONTACT_HR)
async def on_contact_hr(message: Message) -> None:
    """Start the HR-request dialog (FR-18: reachable from every screen)."""
    await get_state_dispenser().set(message.peer_id, BotStates.HR_REQUEST_NAME)
    await message.answer(
        "💬 Формирование обращения в HR\n\n"
        "Шаг 1 из 5. Введите ФИО сотрудника:",
        keyboard=_name_input_kb(),
    )


# ── back navigation within dialog ─────────────────────────────────


@bl.message(PayloadCmdRule(CMD_HR_BACK))
async def on_hr_back(message: Message, payload_data: dict) -> None:
    step = payload_data.get("step", "start")

    if step == "start":
        # back from topic → re-ask name
        await get_state_dispenser().set(message.peer_id, BotStates.HR_REQUEST_NAME)
        await message.answer(
            "Шаг 1 из 5. Введите ФИО сотрудника:",
            keyboard=_name_input_kb(),
        )
    elif step == "details":
        # back from entity → re-ask details
        ctx = await get_state_dispenser().get(message.peer_id)
        payload = ctx.payload if ctx else {}
        await get_state_dispenser().set(
            message.peer_id,
            BotStates.HR_REQUEST_DETAILS,
            **{k: v for k, v in payload.items() if k in ("name", "topic")},
        )
        await message.answer(
            "Шаг 3 из 5. Опишите суть обращения:",
            keyboard=_name_input_kb(),
        )
    elif step == "entity":
        # back from urgency → re-ask entity
        ctx = await get_state_dispenser().get(message.peer_id)
        payload = ctx.payload if ctx else {}
        await get_state_dispenser().set(
            message.peer_id,
            BotStates.HR_REQUEST_ENTITY,
            **{k: v for k, v in payload.items() if k in ("name", "topic", "details")},
        )
        await message.answer(
            "Шаг 4 из 5. Выберите юридическое лицо:",
            keyboard=hr_entity_kb().get_json(),
        )


# ── restart dialog ─────────────────────────────────────────────────


@bl.message(payload=CMD_HR_RESTART)
async def on_hr_restart(message: Message) -> None:
    await get_state_dispenser().set(message.peer_id, BotStates.HR_REQUEST_NAME)
    await message.answer(
        "↩️ Начинаем заново.\n\nШаг 1 из 5. Введите ФИО сотрудника:",
        keyboard=_name_input_kb(),
    )


# ── step 1: capture name ──────────────────────────────────────────


@bl.message(state=BotStates.HR_REQUEST_NAME)
async def on_hr_name(message: Message) -> None:
    name = message.text.strip()
    if not name or len(name) < 2:
        await message.answer("Пожалуйста, введите ФИО (минимум 2 символа):")
        return
    await get_state_dispenser().set(
        message.peer_id, BotStates.HR_REQUEST_TOPIC, name=name,
    )
    await message.answer(
        "Шаг 2 из 5. Выберите тему обращения:",
        keyboard=hr_topic_kb().get_json(),
    )


# ── step 2: capture topic ─────────────────────────────────────────


@bl.message(state=BotStates.HR_REQUEST_TOPIC)
async def on_hr_topic(message: Message) -> None:
    topic = message.text.strip()
    if topic not in HR_REQUEST_TOPICS:
        await message.answer(
            "Пожалуйста, выберите тему из предложенных кнопок:",
            keyboard=hr_topic_kb().get_json(),
        )
        return
    ctx = await get_state_dispenser().get(message.peer_id)
    prev = ctx.payload if ctx else {}
    await get_state_dispenser().set(
        message.peer_id,
        BotStates.HR_REQUEST_DETAILS,
        name=prev.get("name", ""),
        topic=topic,
    )
    await message.answer(
        "Шаг 3 из 5. Опишите суть обращения:",
        keyboard=_name_input_kb(),
    )


# ── step 3: capture details ───────────────────────────────────────


@bl.message(state=BotStates.HR_REQUEST_DETAILS)
async def on_hr_details(message: Message) -> None:
    details = message.text.strip()
    if not details or len(details) < 5:
        await message.answer("Пожалуйста, опишите суть подробнее (минимум 5 символов):")
        return
    ctx = await get_state_dispenser().get(message.peer_id)
    prev = ctx.payload if ctx else {}
    await get_state_dispenser().set(
        message.peer_id,
        BotStates.HR_REQUEST_ENTITY,
        name=prev.get("name", ""),
        topic=prev.get("topic", ""),
        details=details,
    )
    await message.answer(
        "Шаг 4 из 5. Выберите юридическое лицо:",
        keyboard=hr_entity_kb().get_json(),
    )


# ── step 4: capture entity ────────────────────────────────────────


@bl.message(state=BotStates.HR_REQUEST_ENTITY)
async def on_hr_entity(message: Message) -> None:
    entity_name = message.text.strip()
    if entity_name not in _ENTITY_SHORT_NAMES:
        await message.answer(
            "Пожалуйста, выберите юрлицо из предложенных кнопок:",
            keyboard=hr_entity_kb().get_json(),
        )
        return
    entity = _ENTITY_BY_SHORT[entity_name]
    ctx = await get_state_dispenser().get(message.peer_id)
    prev = ctx.payload if ctx else {}
    await get_state_dispenser().set(
        message.peer_id,
        BotStates.HR_REQUEST_URGENCY,
        name=prev.get("name", ""),
        topic=prev.get("topic", ""),
        details=prev.get("details", ""),
        entity_id=entity.id,
    )
    await message.answer(
        "Шаг 5 из 5. Выберите срочность обращения:",
        keyboard=hr_urgency_kb().get_json(),
    )


# ── step 5: capture urgency → show confirmation ───────────────────


@bl.message(state=BotStates.HR_REQUEST_URGENCY)
async def on_hr_urgency(message: Message) -> None:
    urgency = message.text.strip()
    if urgency not in HR_REQUEST_URGENCY_OPTIONS:
        await message.answer(
            "Пожалуйста, выберите срочность из предложенных кнопок:",
            keyboard=hr_urgency_kb().get_json(),
        )
        return
    ctx = await get_state_dispenser().get(message.peer_id)
    prev = ctx.payload if ctx else {}
    entity = ENTITY_BY_ID.get(prev.get("entity_id", 0))
    if entity is None:
        await message.answer("Ошибка. Начните заново.", keyboard=main_menu_kb().get_json())
        await _clear_state(message.peer_id)
        return

    preview = format_hr_request(
        name=prev.get("name", ""),
        topic=prev.get("topic", ""),
        details=prev.get("details", ""),
        entity=entity,
        urgency=urgency,
    )

    await get_state_dispenser().set(
        message.peer_id,
        BotStates.HR_REQUEST_CONFIRM,
        name=prev.get("name", ""),
        topic=prev.get("topic", ""),
        details=prev.get("details", ""),
        entity_id=entity.id,
        urgency=urgency,
    )
    await message.answer(
        f"Проверьте обращение:\n\n{preview}",
        keyboard=hr_confirm_kb().get_json(),
    )


# ── step 6: confirm ───────────────────────────────────────────────


@bl.message(payload=CMD_HR_CONFIRM)
async def on_hr_confirm(message: Message) -> None:
    ctx = await get_state_dispenser().get(message.peer_id)
    if ctx is None:
        await message.answer("Сессия истекла. Начните заново.", keyboard=main_menu_kb().get_json())
        return

    prev = ctx.payload
    entity = ENTITY_BY_ID.get(prev.get("entity_id", 0))
    if entity is None:
        await message.answer("Ошибка. Начните заново.", keyboard=main_menu_kb().get_json())
        await _clear_state(message.peer_id)
        return

    final_text = format_hr_request(
        name=prev.get("name", ""),
        topic=prev.get("topic", ""),
        details=prev.get("details", ""),
        entity=entity,
        urgency=prev.get("urgency", ""),
    )

    await _clear_state(message.peer_id)
    await message.answer(
        f"✅ Обращение сформировано!\n\n{final_text}",
        keyboard=hr_done_kb().get_json(),
    )
    logger.info("HR request formed by peer_id=%s, topic=%s", message.peer_id, prev.get("topic"))
