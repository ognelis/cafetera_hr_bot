"""Pay & bonus flow handlers — S-40 (FR-9, FR-10).

Flow: CMD_PAY -> pay menu -> overtime RAG / bonus RAG.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.integrations.vk.handlers import send_rag_answer
from app.integrations.vk.keyboards import (
    CMD_PAY,
    CMD_PAY_BONUS,
    CMD_PAY_OVERTIME,
    pay_menu_kb,
)

bl = BotLabeler()


# -- S-40: entry -> pay section menu -----------------------------------


@bl.message(payload=CMD_PAY)
async def on_pay(message: Message) -> None:
    await message.answer(
        "💰 Оплата и премии\n\nВыберите тему:",
        keyboard=pay_menu_kb().get_json(),
    )


# -- FR-9: overtime & weekend pay -- RAG (Block 8) ---------------------


@bl.message(payload=CMD_PAY_OVERTIME)
async def on_pay_overtime(message: Message) -> None:
    await send_rag_answer(message, question="Оплата сверхурочных и выходных", back_payload=CMD_PAY, category="pay")


# -- FR-10: bonus conditions -- RAG (Block 7) -------------------------


@bl.message(payload=CMD_PAY_BONUS)
async def on_pay_bonus(message: Message) -> None:
    await send_rag_answer(message, question="Условия премирования", back_payload=CMD_PAY, category="pay")
