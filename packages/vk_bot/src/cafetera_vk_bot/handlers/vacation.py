"""Vacation flow handlers — S-30 partial (FR-7, FR-8, FR-11).

Flow: CMD_VACATION → vacation menu → entity selection → disclaimer + template.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from cafetera_vk_bot.attachments import send_category_document
from cafetera_vk_bot.domain.content import vacation_template_text
from cafetera_vk_bot.handlers import (
    get_category_file_service,
    get_entity_or_error,
    send_rag_answer,
)
from cafetera_vk_bot.keyboards import (
    CMD_VACATION,
    CMD_VACATION_RAG,
    CMD_VACATION_SCHEDULE,
    CMD_VACATION_SELECT,
    CMD_VACATION_TEMPLATE,
    entity_select_kb,
    stub_kb,
    vacation_menu_kb,
    vacation_type_kb,
)
from cafetera_vk_bot.rules import PayloadCmdRule

bl = BotLabeler()


# ── S-30: entry → vacation menu ────────────────────────────────────


@bl.message(payload=CMD_VACATION)
async def on_vacation(message: Message) -> None:
    await message.answer(
        "🏖 Отпуск\n\nВыберите действие:",
        keyboard=vacation_menu_kb().get_json(),
    )


# ── FR-8: select vacation type for leave application template ──────


@bl.message(payload=CMD_VACATION_SELECT)
async def on_vacation_select(message: Message) -> None:
    await message.answer(
        "📄 Заявление на отпуск\n\nВыберите тип отпуска:",
        keyboard=vacation_type_kb().get_json(),
    )


# ── FR-8: vacation type selected → entity selection ────────────────


@bl.message(PayloadCmdRule("vacation_type"))
async def on_vacation_type(message: Message, payload_data: dict) -> None:
    vtype = payload_data.get("vtype", "paid")
    vtype_label = (
        "За свой счет"
        if vtype == "unpaid"
        else "Оплачиваемый"
    )
    await message.answer(
        f"📄 Заявление на отпуск — {vtype_label}\n\nВыберите юридическое лицо:",
        keyboard=entity_select_kb(
            CMD_VACATION_TEMPLATE,
            back_payload=CMD_VACATION_SELECT,
            extra_payload={"vtype": vtype},
        ).get_json(),
    )


# ── entity selected → disclaimer + file stub ──────────────────────


@bl.message(PayloadCmdRule(CMD_VACATION_TEMPLATE))
async def on_vacation_template(message: Message, payload_data: dict) -> None:
    entity_id: int = payload_data.get("entity", 0)
    entity = await get_entity_or_error(
        message, entity_id, back_payload=CMD_VACATION_SELECT
    )
    if entity is None:
        return
    vtype = payload_data.get("vtype", "paid")
    vtype_label = (
        "За свой счет"
        if vtype == "unpaid"
        else "Оплачиваемый"
    )

    # Map vtype to subcategory
    subcategory = "vacation_unpaid" if vtype == "unpaid" else "vacation_paid"

    # Try to send document attachment first, fall back to text
    caption = (
        f"📄 Шаблон заявления на отпуск — {entity.full_name}\n"
        f"Тип: {vtype_label}\n\n"
    )
    sent = await send_category_document(
        message,
        get_category_file_service(),
        category="vacation",
        subcategory=subcategory,
        entity_id=entity_id,
        caption=caption,
    )
    if not sent:
        await message.answer(
            vacation_template_text(entity, vtype),
            keyboard=stub_kb(back_payload=CMD_VACATION_SELECT).get_json(),
        )


# ── FR-7: leave procedure — RAG (Block 7) ─────────────────────────


@bl.message(payload=CMD_VACATION_RAG)
async def on_vacation_rag(message: Message) -> None:
    await send_rag_answer(message, question="Порядок оформления отпуска", back_payload=CMD_VACATION)


# ── FR-11: vacation schedule navigator — RAG (Block 8) ─────────────


@bl.message(payload=CMD_VACATION_SCHEDULE)
async def on_vacation_schedule(message: Message) -> None:
    await send_rag_answer(
        message, question="Навигатор по графику отпусков", back_payload=CMD_VACATION,
    )
