"""Tests for Block 2 keyboard builders and new payload constants."""

import json

from vkbottle import Keyboard

from app.domain.entities import ENTITIES
from app.integrations.vk.keyboards import (
    CMD_FIRE_BYPASS,
    CMD_FIRE_CHECKLIST,
    CMD_FIRE_GROUNDS,
    CMD_FIRE_RAG,
    CMD_HIRE,
    CMD_HOME,
    CMD_VACATION_RAG,
    CMD_VACATION_SCHEDULE,
    CMD_VACATION_SELECT,
    entity_select_kb,
    fire_menu_kb,
    hire_actions_kb,
    vacation_menu_kb,
)


def _parse(kb: Keyboard) -> dict:
    return json.loads(kb.get_json())


def _all_buttons(data: dict) -> list[dict]:
    return [btn for row in data["buttons"] for btn in row]


def _labels(data: dict) -> list[str]:
    return [btn["action"]["label"] for btn in _all_buttons(data)]


def _payloads(data: dict) -> list[dict]:
    return [btn["action"]["payload"] for btn in _all_buttons(data)]


def _has_label(labels: list[str], substring: str) -> bool:
    return any(substring in label for label in labels)


# ── entity_select_kb ───────────────────────────────────────────────


class TestEntitySelectKb:
    def test_has_four_entity_buttons(self):
        data = _parse(entity_select_kb("test_cmd", back_payload=CMD_HOME))
        # 4 entity + service row buttons
        entity_btns = [
            btn for btn in _all_buttons(data)
            if btn["action"]["payload"].get("cmd") == "test_cmd"
        ]
        assert len(entity_btns) == 4

    def test_entity_names_match(self):
        data = _parse(entity_select_kb("test_cmd", back_payload=CMD_HOME))
        labels = _labels(data)
        for entity in ENTITIES:
            assert entity.full_name in labels

    def test_entity_ids_in_payloads(self):
        data = _parse(entity_select_kb("test_cmd", back_payload=CMD_HOME))
        entity_payloads = [
            btn["action"]["payload"]
            for btn in _all_buttons(data)
            if btn["action"]["payload"].get("cmd") == "test_cmd"
        ]
        ids = {p["entity"] for p in entity_payloads}
        assert ids == {e.id for e in ENTITIES}

    def test_has_service_row(self):
        data = _parse(entity_select_kb("test_cmd", back_payload=CMD_HOME))
        labels = _labels(data)
        assert _has_label(labels, "Главное меню")

    def test_has_back_button(self):
        data = _parse(entity_select_kb("test_cmd", back_payload=CMD_HOME))
        labels = _labels(data)
        assert _has_label(labels, "Назад")


# ── hire_actions_kb ────────────────────────────────────────────────


class TestHireActionsKb:
    def test_has_three_action_buttons(self):
        data = _parse(hire_actions_kb(1))
        labels = _labels(data)
        assert _has_label(labels, "Чек-лист документов")
        assert _has_label(labels, "Шаблон трудового договора")
        assert _has_label(labels, "Онбординг")

    def test_entity_id_in_payloads(self):
        data = _parse(hire_actions_kb(2))
        action_payloads = [
            btn["action"]["payload"]
            for btn in _all_buttons(data)
            if btn["action"]["payload"].get("entity") == 2
        ]
        assert len(action_payloads) == 3

    def test_back_goes_to_hire(self):
        data = _parse(hire_actions_kb(1))
        back_btns = [
            btn for btn in _all_buttons(data)
            if "Назад" in btn["action"]["label"]
        ]
        assert len(back_btns) == 1
        assert back_btns[0]["action"]["payload"] == CMD_HIRE


# ── fire_menu_kb ───────────────────────────────────────────────────


class TestFireMenuKb:
    def test_has_four_action_buttons(self):
        data = _parse(fire_menu_kb())
        labels = _labels(data)
        assert _has_label(labels, "Чек-лист последнего дня")
        assert _has_label(labels, "Обходной лист")
        assert _has_label(labels, "Увольнение по собственному")
        assert _has_label(labels, "Основания увольнения")

    def test_checklist_payload(self):
        data = _parse(fire_menu_kb())
        assert CMD_FIRE_CHECKLIST in _payloads(data)

    def test_bypass_payload(self):
        data = _parse(fire_menu_kb())
        assert CMD_FIRE_BYPASS in _payloads(data)

    def test_rag_payload(self):
        data = _parse(fire_menu_kb())
        assert CMD_FIRE_RAG in _payloads(data)

    def test_grounds_payload(self):
        data = _parse(fire_menu_kb())
        assert CMD_FIRE_GROUNDS in _payloads(data)

    def test_back_goes_home(self):
        data = _parse(fire_menu_kb())
        back_btns = [
            btn for btn in _all_buttons(data)
            if "Назад" in btn["action"]["label"]
        ]
        assert len(back_btns) == 1
        assert back_btns[0]["action"]["payload"] == CMD_HOME


# ── vacation_menu_kb ───────────────────────────────────────────────


class TestVacationMenuKb:
    def test_has_three_action_buttons(self):
        data = _parse(vacation_menu_kb())
        labels = _labels(data)
        assert _has_label(labels, "Заявление на отпуск")
        assert _has_label(labels, "Порядок оформления")
        assert _has_label(labels, "Навигатор по графику отпусков")

    def test_template_goes_to_select(self):
        data = _parse(vacation_menu_kb())
        assert CMD_VACATION_SELECT in _payloads(data)

    def test_rag_payload(self):
        data = _parse(vacation_menu_kb())
        assert CMD_VACATION_RAG in _payloads(data)

    def test_schedule_payload(self):
        data = _parse(vacation_menu_kb())
        assert CMD_VACATION_SCHEDULE in _payloads(data)



