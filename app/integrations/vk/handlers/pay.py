"""Pay & bonus flow handlers — S-40 (FR-9, FR-10).

Flow: CMD_PAY -> pay menu -> overtime RAG stub / bonus RAG stub.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.domain import qa_service
from app.domain.content import rag_stub
from app.integrations.vk.keyboards import (
    CMD_PAY,
    CMD_PAY_BONUS,
    CMD_PAY_OVERTIME,
    pay_menu_kb,
    stub_kb,
)

bl = BotLabeler()


# -- S-40: entry -> pay section menu -----------------------------------


@bl.message(payload=CMD_PAY)
async def on_pay(message: Message) -> None:
    await message.answer(
        "💰 Оплата и премии\n\nВыберите тему:",
        keyboard=pay_menu_kb().get_json(),
    )


# -- FR-9: overtime & weekend pay -- RAG stub --------------------------


@bl.message(payload=CMD_PAY_OVERTIME)
async def on_pay_overtime(message: Message) -> None:
    await message.answer(
        rag_stub("Оплата сверхурочных и выходных"),
        keyboard=stub_kb(back_payload=CMD_PAY).get_json(),
    )


# -- FR-10: bonus conditions -- RAG (Block 7) -------------------------


@bl.message(payload=CMD_PAY_BONUS)
async def on_pay_bonus(message: Message) -> None:
    await message.ctx_api.messages.set_activity(type="typing", peer_id=message.peer_id)
    answer = await qa_service.ask("Условия премирования")
    await message.answer(
        answer,
        keyboard=stub_kb(back_payload=CMD_PAY).get_json(),
    )
