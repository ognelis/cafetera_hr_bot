"""Static content: checklists, disclaimers, and HR-request topics.

All long texts live here so that handlers stay thin (00-architecture).
"""

from __future__ import annotations

from app.domain.entities import LegalEntity

# ── FR-17 disclaimer (shown before any document template) ─────────

TEMPLATE_FILE_STUB = (
    "📄 Файл шаблона будет доступен после подключения хранилища документов.\n"
    "Обратитесь в HR для получения шаблона."
)
# NOTE: These static text functions serve as fallback when no category file is uploaded.
# When a document exists in the category file system, it is sent as a VK attachment instead.


# ── 👤 Hire: document checklists (FR-2, FR-3) ────────────────────

_HIRE_CHECKLIST_COMMON = (
    "✅ Чек-лист документов для оформления:\n\n"
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


def hire_checklist(entity: LegalEntity) -> str:
    """Return document checklist text for the given entity."""
    return f"📋 Оформление в {entity.full_name}\n\n{_HIRE_CHECKLIST_COMMON}"


# ── 👤 Hire: onboarding checklist (FR-14) ─────────────────────────

_ONBOARDING_CHECKLIST = (
    "🗒️ Онбординг-чек-лист нового сотрудника:\n\n"
    "1. Подписание трудового договора и приказа о приёме\n"
    "2. Ознакомление с правилами внутреннего трудового распорядка\n"
    "3. Инструктаж по охране труда и пожарной безопасности\n"
    "4. Получение пропуска / доступа к рабочему месту\n"
    "5. Знакомство с командой и наставником\n"
    "6. Настройка рабочих инструментов и доступов\n"
    "7. Ознакомление с графиком работы и сменами\n"
    "8. Прохождение вводного обучения (стандарты обслуживания)"
)


def onboarding_checklist(entity: LegalEntity) -> str:
    return f"🗒️ Онбординг в {entity.full_name}\n\n{_ONBOARDING_CHECKLIST}"


# ── 👤 Hire: contract template (FR-4) ─────────────────────────────


def hire_contract_text(entity: LegalEntity) -> str:
    """Return contract template text. Fallback when no category file is uploaded."""
    return (
        f"📄 Шаблон трудового договора — {entity.full_name}\n\n"
        f"{TEMPLATE_FILE_STUB}"
    )


# ── 🏖 Vacation: leave application template (FR-8) ────────────────


def vacation_template_text(entity: LegalEntity, vtype: str = "paid") -> str:
    """Return vacation application template text. Fallback when no category file is uploaded."""
    vtype_label = (
        "За свой счет"
        if vtype == "unpaid"
        else "Оплачиваемый"
    )
    return (
        f"📄 Шаблон заявления на отпуск — {entity.full_name}\n"
        f"Тип: {vtype_label}\n\n"
        f"{TEMPLATE_FILE_STUB}"
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


# ── Error states (Block 4, section 4.5) ──────────────────────────

ERR_DOCUMENT_UNAVAILABLE = (
    "⚠️ Не удалось получить ответ.\n\n"
    "Пожалуйста, задайте вопрос позже."
)

ERR_NO_ANSWER = (
    "🔍 К сожалению, точного ответа не найдено.\n\n"
    "Рекомендуем обратиться в HR-отдел компании."
)

ERR_INTEGRATION_REQUIRED = (
    "🔒 Для получения этой информации требуется доступ к внутренним системам "
    "(1С ЗУП, кадровый учёт).\n\n"
    "Обратитесь в HR-отдел — сотрудники помогут с вашим запросом."
)

