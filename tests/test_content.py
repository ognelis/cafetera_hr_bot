"""Tests for app.domain.content — static content and formatters."""

from app.domain.content import (
    TEMPLATE_DISCLAIMER,
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


class TestVacationContent:
    def test_template_contains_entity(self):
        entity = ENTITIES[3]
        text = vacation_template_text(entity)
        assert entity.full_name in text

    def test_template_contains_disclaimer(self):
        text = vacation_template_text(ENTITIES[0])
        assert TEMPLATE_DISCLAIMER in text



