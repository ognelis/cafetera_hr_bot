"""Keyboard builders for the VK bot.

Every screen gets service buttons (Back, Home) via
``with_service_row``.  The main menu keyboard is built by ``main_menu_kb``.
"""

from __future__ import annotations

from vkbottle import Keyboard, KeyboardButtonColor, Text

from cafetera_vk_bot.domain.entities import ENTITIES

# ── payload constants ──────────────────────────────────────────────

CMD_HOME = {"cmd": "home"}
CMD_BACK = {"cmd": "back"}

CMD_HIRE = {"cmd": "hire"}
CMD_FIRE = {"cmd": "fire"}
CMD_VACATION = {"cmd": "vacation"}
CMD_PAY = {"cmd": "pay"}
CMD_SICK = {"cmd": "sick"}
CMD_PROBATION = {"cmd": "probation"}
CMD_ASK = {"cmd": "ask"}

# ── hire sub-action payloads ───────────────────────────────────────

CMD_HIRE_CHECKLIST = "hire_checklist"
CMD_HIRE_CONTRACT = "hire_contract"
CMD_HIRE_ONBOARDING = "hire_onboarding"

# ── pay sub-action payloads ─────────────────────────────────────────

CMD_PAY_OVERTIME = {"cmd": "pay_overtime"}   # FR-9: overtime & weekend pay
CMD_PAY_BONUS = {"cmd": "pay_bonus"}         # FR-10: bonus conditions

# ── fire sub-action payloads ───────────────────────────────────────

CMD_FIRE_RAG = {"cmd": "fire_rag"}  # stub → Block 3 (kept for compatibility)
CMD_FIRE_GROUNDS = {"cmd": "fire_grounds"}  # FR-12: dismissal grounds (Block 5)

# FR-5: voluntary dismissal — entity selection → template
CMD_FIRE_RESIGNATION = {"cmd": "fire_resignation"}
FIRE_RESIGNATION_ENTITY_CMD = "fire_resignation_entity"

# ── vacation sub-action payloads ───────────────────────────────────

CMD_VACATION_SELECT = {"cmd": "vacation_select"}  # opens vacation type selection
CMD_VACATION_TYPE = {"cmd": "vacation_type"}  # vacation type selection step
CMD_VACATION_TEMPLATE = "vacation_template"  # cmd value for PayloadCmdRule
CMD_VACATION_RAG = {"cmd": "vacation_rag"}  # stub → Block 3
CMD_VACATION_SCHEDULE = {"cmd": "vacation_schedule"}  # FR-11: schedule navigator (Block 5)

# ── service row builder ────────────────────────────────────────────


def with_service_row(
    kb: Keyboard,
    *,
    back_payload: dict | None = None,
    show_home: bool = True,
) -> Keyboard:
    """Append the standard service-button row to *kb* and return it.

    UXR-5: Back / Home must be reachable from every screen.
    """
    kb.row()
    if back_payload is not None:
        kb.add(Text("⬅ Назад", payload=back_payload))
    if show_home:
        kb.add(Text("🏠 Главное меню", payload=CMD_HOME))
    return kb


# ── main menu ──────────────────────────────────────────────────────


def main_menu_kb() -> Keyboard:
    """Build the S-01 main-menu keyboard (7 sections, FR-1)."""
    kb = Keyboard(one_time=False, inline=False)

    kb.add(
        Text("👤 Приём сотрудника", payload=CMD_HIRE),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    kb.add(
        Text("🚪 Увольнение", payload=CMD_FIRE),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    kb.add(
        Text("🏖 Отпуск", payload=CMD_VACATION),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    kb.add(
        Text("💰 Оплата и премии", payload=CMD_PAY),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    kb.add(
        Text("🏥 Больничный / ЭЛН", payload=CMD_SICK),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    kb.add(
        Text("📝 Испытательный срок", payload=CMD_PROBATION),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    kb.add(Text("❓ Задать вопрос", payload=CMD_ASK))

    return kb


# ── convenience: keyboard with only service row ───────────────────


def stub_kb(*, back_payload: dict | None = None) -> Keyboard:
    """Minimal keyboard for stub / placeholder screens."""
    kb = Keyboard(one_time=False, inline=False)
    return with_service_row(kb, back_payload=back_payload)


# ── entity selection keyboard ──────────────────────────────────────


def entity_select_kb(
    cmd: str,
    *,
    back_payload: dict,
    extra_payload: dict | None = None,
) -> Keyboard:
    """4 legal-entity buttons (NFR-7) + service row.

    *cmd* is the ``cmd`` value embedded in each button payload so the
    receiving handler can distinguish contexts (e.g. ``hire_entity``
    vs ``vacation_template``).

    *extra_payload* is merged into each button's payload to carry
    additional context (e.g. vacation type) through the flow.
    """
    kb = Keyboard(one_time=False, inline=False)
    for i, entity in enumerate(ENTITIES):
        if i > 0:
            kb.row()
        payload = {"cmd": cmd, "entity": entity.id}
        if extra_payload:
            payload.update(extra_payload)
        kb.add(Text(entity.full_name, payload=payload))
    return with_service_row(kb, back_payload=back_payload)


# ── hire action menu ───────────────────────────────────────────────


def hire_actions_kb(entity_id: int) -> Keyboard:
    """S-11 action menu after entity is selected (FR-2, FR-3, FR-4, FR-14)."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(
        Text("✅ Чек-лист документов", payload={"cmd": CMD_HIRE_CHECKLIST, "entity": entity_id}),
    )
    kb.row()
    contract_payload = {"cmd": CMD_HIRE_CONTRACT, "entity": entity_id}
    kb.add(
        Text("📄 Шаблон трудового договора", payload=contract_payload),
    )
    kb.row()
    kb.add(
        Text("🗒️ Онбординг-чек-лист", payload={"cmd": CMD_HIRE_ONBOARDING, "entity": entity_id}),
    )
    return with_service_row(kb, back_payload=CMD_HIRE)


# ── fire menu ──────────────────────────────────────────────────────


def fire_menu_kb() -> Keyboard:
    """S-20 fire section menu (FR-5, FR-12)."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🚪 Увольнение по собственному", payload=CMD_FIRE_RESIGNATION))
    kb.row()
    kb.add(Text("📖 Основания увольнения", payload=CMD_FIRE_GROUNDS))
    return with_service_row(kb, back_payload=CMD_HOME)


# ── vacation menu ──────────────────────────────────────────────────


def vacation_menu_kb() -> Keyboard:
    """S-30 vacation section menu (FR-7, FR-8, FR-11)."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📄 Заявление на отпуск", payload=CMD_VACATION_SELECT))
    kb.row()
    kb.add(Text("🏖 Порядок оформления отпуска", payload=CMD_VACATION_RAG))
    kb.row()
    kb.add(Text("🗓️ Навигатор по графику отпусков", payload=CMD_VACATION_SCHEDULE))
    return with_service_row(kb, back_payload=CMD_HOME)


def vacation_type_kb() -> Keyboard:
    """Vacation type selection keyboard (FR-8 intermediate step)."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(
        Text(
            "💰 Оплачиваемый",
            payload={"cmd": "vacation_type", "vtype": "paid"},
        )
    )
    kb.row()
    kb.add(
        Text(
            "💸 За свой счет",
            payload={"cmd": "vacation_type", "vtype": "unpaid"},
        )
    )
    return with_service_row(kb, back_payload=CMD_VACATION)


# ── pay menu ──────────────────────────────────────────────────────


def pay_menu_kb() -> Keyboard:
    """S-40 pay section menu (FR-9, FR-10)."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("💵 Оплата сверхурочных и выходных", payload=CMD_PAY_OVERTIME))
    kb.row()
    kb.add(Text("🏆 Условия премирования", payload=CMD_PAY_BONUS))
    return with_service_row(kb, back_payload=CMD_HOME)


# ── ask question keyboard ─────────────────────────────────────────

# scenario_id → (label, payload) for ask-result suggestion buttons (Block 9)
_SCENARIO_BUTTONS: dict[str, tuple[str, dict]] = {
    "hire": ("👤 Приём сотрудника", CMD_HIRE),
    "fire": ("🚪 Увольнение", CMD_FIRE),
    "vacation": ("🏖 Отпуск", CMD_VACATION),
    "pay": ("💰 Оплата и премии", CMD_PAY),
    "sick": ("🏥 Больничный / ЭЛН", CMD_SICK),
    "probation": ("📝 Испытательный срок", CMD_PROBATION),
}


def ask_input_kb() -> Keyboard:
    """Keyboard shown while user is typing a free-text question."""
    kb = Keyboard(one_time=False, inline=False)
    return with_service_row(kb, back_payload=CMD_HOME)


def ask_result_kb(*, scenario_id: str | None = None) -> Keyboard:
    """Keyboard shown after a free-text RAG answer (Block 9).

    If *scenario_id* matches a clickable scenario, an extra navigation
    button is added so the user can jump to the dedicated section.
    """
    kb = Keyboard(one_time=False, inline=False)
    if scenario_id and scenario_id in _SCENARIO_BUTTONS:
        label, payload = _SCENARIO_BUTTONS[scenario_id]
        kb.add(Text(label, payload=payload))
    return with_service_row(kb, back_payload=CMD_ASK)
