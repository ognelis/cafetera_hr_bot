"""Tests for app.domain.content — static content and formatters."""

from app.domain.content import (
    FIRE_BYPASS_SHEET_TEXT,
    FIRE_LAST_DAY_CHECKLIST,
    HR_REQUEST_TOPICS,
    HR_REQUEST_URGENCY_OPTIONS,
    TEMPLATE_DISCLAIMER,
    format_hr_request,
    hire_checklist,
    hire_contract_text,
    onboarding_checklist,
    vacation_template_text,
)
from app.domain.entities import ENTITIES


class TestHireContent:
    def test_checklist_contains_entity_name(self):
        entity = ENTITIES[0]
        text = hire_checklist(entity)
        assert entity.full_name in text

    def test_checklist_contains_passport(self):
        text = hire_checklist(ENTITIES[0])
        assert "Паспорт" in text

    def test_contract_text_contains_disclaimer(self):
        text = hire_contract_text(ENTITIES[0])
        assert "Дисклеймер" in text

    def test_contract_text_contains_entity(self):
        entity = ENTITIES[1]
        text = hire_contract_text(entity)
        assert entity.full_name in text

    def test_onboarding_contains_entity(self):
        entity = ENTITIES[2]
        text = onboarding_checklist(entity)
        assert entity.full_name in text


class TestFireContent:
    def test_last_day_checklist_not_empty(self):
        assert len(FIRE_LAST_DAY_CHECKLIST) > 50

    def test_last_day_checklist_has_steps(self):
        assert "1." in FIRE_LAST_DAY_CHECKLIST

    def test_bypass_sheet_has_disclaimer(self):
        assert "Дисклеймер" in FIRE_BYPASS_SHEET_TEXT


class TestVacationContent:
    def test_template_contains_entity(self):
        entity = ENTITIES[3]
        text = vacation_template_text(entity)
        assert entity.full_name in text

    def test_template_contains_disclaimer(self):
        text = vacation_template_text(ENTITIES[0])
        assert TEMPLATE_DISCLAIMER in text


class TestHrRequest:
    def test_topics_not_empty(self):
        assert len(HR_REQUEST_TOPICS) >= 3

    def test_urgency_options_count(self):
        assert len(HR_REQUEST_URGENCY_OPTIONS) == 2

    def test_format_hr_request_contains_all_fields(self):
        entity = ENTITIES[0]
        text = format_hr_request(
            name="Иванов Иван Иванович",
            topic="Отпуск",
            details="Прошу уточнить остаток дней.",
            entity=entity,
            urgency="🔴 Срочно",
        )
        assert "Иванов Иван Иванович" in text
        assert "Отпуск" in text
        assert "Прошу уточнить" in text
        assert entity.full_name in text
        assert "Срочно" in text

    def test_format_hr_request_has_header(self):
        entity = ENTITIES[0]
        text = format_hr_request(
            name="Тест", topic="Тест", details="Тест", entity=entity, urgency="Тест",
        )
        assert "Обращение в HR" in text
