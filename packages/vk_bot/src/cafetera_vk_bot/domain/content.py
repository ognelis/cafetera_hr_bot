"""Static content: checklists, disclaimers, and HR-request topics.

All long texts live here so that handlers stay thin (00-architecture).
VK-specific content — shared error constants moved to cafetera_core.domain.errors.
"""

from __future__ import annotations

from vkbottle.tools import Format, bold

from cafetera_vk_bot.domain.entities import LegalEntity

# ── FR-17 disclaimer (shown before any document template) ─────────

TEMPLATE_FILE_STUB = (
    "📄 Файл шаблона будет доступен после подключения хранилища документов.\n"
    "Обратитесь в HR для получения шаблона."
)
# NOTE: These static text functions serve as fallback when no category file is uploaded.
# When a document exists in the category file system, it is sent as a VK attachment instead.


# ── 👤 Hire: document checklists (FR-2, FR-3) ────────────────────

_HIRE_CHECKLIST_ITEMS = (
    "1. Паспорт РФ (оригинал + копия)\n"
    "2. СНИЛС\n"
    "3. ИНН\n"
    "4. Трудовая книжка или сведения о трудовой деятельности (СТД-Р)\n"
    "5. Документ об образовании (при необходимости)\n"
    "6. Военный билет (для военнообязанных)\n"
    "7. Фотография 3×4 — 2 шт.\n"
    "8. Справка об отсутствии судимости (для отдельных должностей)\n"
    "9. Медицинская книжка (для работы в общепите)"
)


def hire_checklist(entity: LegalEntity) -> Format:
    """Return document checklist text for the given entity."""
    return (
        "📋 " + bold(f"Оформление в {entity.full_name}")
        + "\n\n✅ " + bold("Чек-лист документов для оформления:")
        + "\n\n" + _HIRE_CHECKLIST_ITEMS
    )


# ── 👤 Hire: onboarding checklist (FR-14) ─────────────────────────

_ONBOARDING_ITEMS = (
    "1. Подписание трудового договора и приказа о приёме\n"
    "2. Ознакомление с правилами внутреннего трудового распорядка\n"
    "3. Инструктаж по охране труда и пожарной безопасности\n"
    "4. Получение пропуска / доступа к рабочему месту\n"
    "5. Знакомство с командой и наставником\n"
    "6. Настройка рабочих инструментов и доступов\n"
    "7. Ознакомление с графиком работы и сменами\n"
    "8. Прохождение вводного обучения (стандарты обслуживания)"
)


def onboarding_checklist(entity: LegalEntity) -> Format:
    """Return onboarding checklist text for the given entity."""
    return (
        "🗒️ " + bold(f"Онбординг в {entity.full_name}")
        + "\n\n🗒️ " + bold("Онбординг-чек-лист нового сотрудника:")
        + "\n\n" + _ONBOARDING_ITEMS
    )


# ── 👤 Hire: contract template (FR-4) ─────────────────────────────


def hire_contract_text(entity: LegalEntity) -> Format:
    """Return contract template text. Fallback when no category file is uploaded."""
    return (
        "📄 " + bold(f"Шаблон трудового договора — {entity.full_name}")
        + "\n\n" + TEMPLATE_FILE_STUB
    )


# ── 🏖 Vacation: leave application template (FR-8) ────────────────


def vacation_template_text(entity: LegalEntity, vtype: str = "paid") -> Format:
    """Return vacation application template text. Fallback when no category file is uploaded."""
    vtype_label = (
        "За свой счет"
        if vtype == "unpaid"
        else "Оплачиваемый"
    )
    return (
        "📄 " + bold(f"Шаблон заявления на отпуск — {entity.full_name}")
        + f"\nТип: {vtype_label}\n\n"
        + TEMPLATE_FILE_STUB
    )


# ── RAG stub (Block 3) — placeholder until real RAG is wired ────


def rag_stub(topic: str) -> str:
    """Return a standardised RAG-stub message for *topic*.

    Used while the knowledge-base pipeline is under development.
    """
    return (
        f"ℹ️ {topic} — ответ формируется через базу знаний "
        "(в разработке).\n"
        "Обратитесь в HR или попробуйте позже."
    )
