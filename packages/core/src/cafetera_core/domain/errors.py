"""Shared error-response constants used by domain services."""

from __future__ import annotations

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
