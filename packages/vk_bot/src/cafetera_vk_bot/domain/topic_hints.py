"""Topic hints — detect clickable-scenario links and background-topic disclaimers.

Block 9: when the user asks a free-text question, the answer may relate to
a clickable scenario (9.1) or a background topic that needs an extra
disclaimer (9.2).  This module provides pure-domain detection logic
without importing transport-layer constants.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TopicHint:
    """Result of topic detection.

    *scenario_id*  — identifier of a clickable scenario (e.g. ``"hire"``,
    ``"fire"``, ``"vacation"``).  ``None`` if no match.

    *disclaimer*   — extra text to append after the RAG answer, or ``None``.
    """

    scenario_id: str | None = None
    disclaimer: str | None = None


# ── clickable-scenario keywords (9.1) ─────────────────────────────

_SCENARIO_KEYWORDS: dict[str, list[str]] = {
    "hire": [
        "приём",
        "прием",
        "оформление сотрудника",
        "трудовой договор",
        "онбординг",
        "принять на работу",
    ],
    "fire": [
        "увольнен",       # stem: увольнение/увольнения/увольнении
        "уволиться",
        "уволить",
        "последний рабочий день",
        "обходной лист",
    ],
    "vacation": [
        "отпуск",
        "отпускны",       # stem: отпускные/отпускных
        "заявление на отпуск",
        "график отпуск",
    ],
    "pay": [
        "зарплат",        # stem: зарплата/зарплаты/зарплату
        "преми",          # stem: премия/премии/премирование/премирования
        "оплата труда",
        "сверхурочн",     # stem: сверхурочные/сверхурочных
    ],
    "sick": [
        "больничн",       # stem: больничный/больничного/больничных
        "элн",
        "электронный листок нетрудоспособности",
        "нетрудоспособност",
    ],
    "probation": [
        "испытательн",    # stem: испытательный/испытательного/испытательном
    ],
}

# ── background-topic keywords & disclaimers (9.2) ────────────────

_BACKGROUND_TOPICS: list[tuple[list[str], str]] = [
    (
        ["перевод сотрудника", "перевод на другую должность", "перевод в другое подразделение"],
        "По этой теме рекомендуем согласовать оформление напрямую с HR.",
    ),
    (
        ["дисциплин", "дисциплинарн", "выговор", "замечание"],
        "По вопросам дисциплинарных процедур обратитесь в HR-отдел.",
    ),
    (
        ["увольнение за прогул", "прогул"],
        "По вопросам увольнения за прогул обратитесь в HR-отдел.",
    ),
]


def detect_topic_hint(question: str) -> TopicHint:
    """Analyse *question* and return a :class:`TopicHint`.

    Detection is intentionally keyword-based to stay deterministic and fast.
    """
    q = question.lower()

    # --- background topic (9.2) takes priority — more specific match ---
    disclaimer: str | None = None
    for keywords, disc in _BACKGROUND_TOPICS:
        if any(kw in q for kw in keywords):
            disclaimer = disc
            break

    # --- clickable scenario (9.1) ---
    scenario_id: str | None = None
    for sid, keywords in _SCENARIO_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            scenario_id = sid
            break

    return TopicHint(scenario_id=scenario_id, disclaimer=disclaimer)
