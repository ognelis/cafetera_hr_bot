"""Keyboard builders for the VK bot.

Every screen gets service buttons (Back, Home, Contact HR) via
``with_service_row``.  The main menu keyboard is built by ``main_menu_kb``.
"""

from __future__ import annotations

from vkbottle import Keyboard, KeyboardButtonColor, Text

# ── payload constants ──────────────────────────────────────────────

CMD_HOME = {"cmd": "home"}
CMD_BACK = {"cmd": "back"}
CMD_CONTACT_HR = {"cmd": "contact_hr"}

CMD_HIRE = {"cmd": "hire"}
CMD_FIRE = {"cmd": "fire"}
CMD_VACATION = {"cmd": "vacation"}
CMD_PAY = {"cmd": "pay"}
CMD_SICK = {"cmd": "sick"}
CMD_PROBATION = {"cmd": "probation"}
CMD_ASK = {"cmd": "ask"}


# ── service row builder ────────────────────────────────────────────


def with_service_row(
    kb: Keyboard,
    *,
    back_payload: dict | None = None,
    show_home: bool = True,
    show_hr: bool = True,
) -> Keyboard:
    """Append the standard service-button row to *kb* and return it.

    UXR-5: Back / Home / Contact HR must be reachable from every screen.
    """
    kb.row()
    if back_payload is not None:
        kb.add(Text("⬅ Назад", payload=back_payload))
    if show_home:
        kb.add(Text("🏠 Главное меню", payload=CMD_HOME))
    if show_hr:
        kb.add(
            Text("💬 Написать в HR", payload=CMD_CONTACT_HR),
            color=KeyboardButtonColor.PRIMARY,
        )
    return kb


# ── main menu ──────────────────────────────────────────────────────


def main_menu_kb() -> Keyboard:
    """Build the S-01 main-menu keyboard (7 sections, FR-1)."""
    kb = Keyboard(one_time=False, inline=False)

    kb.add(
        Text("👤 Приём сотрудника", payload=CMD_HIRE),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(
        Text("🚪 Увольнение", payload=CMD_FIRE),
        color=KeyboardButtonColor.PRIMARY,
    )

    kb.row()
    kb.add(
        Text("🏖 Отпуск", payload=CMD_VACATION),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(
        Text("💰 Оплата и премии", payload=CMD_PAY),
        color=KeyboardButtonColor.PRIMARY,
    )

    kb.row()
    kb.add(
        Text("🏥 Больничный / ЭЛН", payload=CMD_SICK),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(
        Text("📝 Испытательный срок", payload=CMD_PROBATION),
        color=KeyboardButtonColor.PRIMARY,
    )

    kb.row()
    kb.add(Text("❓ Задать вопрос", payload=CMD_ASK))

    kb.row()
    kb.add(
        Text("💬 Написать в HR", payload=CMD_CONTACT_HR),
        color=KeyboardButtonColor.POSITIVE,
    )

    return kb


# ── convenience: keyboard with only service row ───────────────────


def stub_kb(*, back_payload: dict | None = None) -> Keyboard:
    """Minimal keyboard for stub / placeholder screens."""
    kb = Keyboard(one_time=False, inline=False)
    return with_service_row(kb, back_payload=back_payload)
