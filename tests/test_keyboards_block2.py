"""Tests for Block 2 keyboard builders and new payload constants."""

import json

from vkbottle import Keyboard

from app.domain.entities import ENTITIES
from app.integrations.vk.keyboards import (
    CMD_FIRE_BYPASS,
    CMD_FIRE_CHECKLIST,
    CMD_FIRE_RAG,
    CMD_HIRE,
    CMD_HOME,
    CMD_HR_CONFIRM,
    CMD_HR_RESTART,
    CMD_VACATION_RAG,
    CMD_VACATION_SELECT,
    entity_select_kb,
    fire_menu_kb,
    hire_actions_kb,
    hr_confirm_kb,
    hr_done_kb,
    hr_entity_kb,
    hr_topic_kb,
    hr_urgency_kb,
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
        assert _has_label(labels, "Написать в HR")

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
    def test_has_three_action_buttons(self):
        data = _parse(fire_menu_kb())
        labels = _labels(data)
        assert _has_label(labels, "Чек-лист последнего дня")
        assert _has_label(labels, "Обходной лист")
        assert _has_label(labels, "Увольнение по собственному")

    def test_checklist_payload(self):
        data = _parse(fire_menu_kb())
        assert CMD_FIRE_CHECKLIST in _payloads(data)

    def test_bypass_payload(self):
        data = _parse(fire_menu_kb())
        assert CMD_FIRE_BYPASS in _payloads(data)

    def test_rag_payload(self):
        data = _parse(fire_menu_kb())
        assert CMD_FIRE_RAG in _payloads(data)

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
    def test_has_two_action_buttons(self):
        data = _parse(vacation_menu_kb())
        labels = _labels(data)
        assert _has_label(labels, "Заявление на отпуск")
        assert _has_label(labels, "Порядок оформления")

    def test_template_goes_to_select(self):
        data = _parse(vacation_menu_kb())
        assert CMD_VACATION_SELECT in _payloads(data)

    def test_rag_payload(self):
        data = _parse(vacation_menu_kb())
        assert CMD_VACATION_RAG in _payloads(data)


# ── hr_topic_kb ────────────────────────────────────────────────────


class TestHrTopicKb:
    def test_has_topic_buttons(self):
        from app.domain.content import HR_REQUEST_TOPICS

        data = _parse(hr_topic_kb())
        labels = _labels(data)
        for topic in HR_REQUEST_TOPICS:
            assert topic in labels

    def test_has_back_button(self):
        data = _parse(hr_topic_kb())
        labels = _labels(data)
        assert _has_label(labels, "Назад")

    def test_has_home_button(self):
        data = _parse(hr_topic_kb())
        labels = _labels(data)
        assert _has_label(labels, "Главное меню")


# ── hr_entity_kb ───────────────────────────────────────────────────


class TestHrEntityKb:
    def test_has_four_entity_buttons(self):
        data = _parse(hr_entity_kb())
        labels = _labels(data)
        for e in ENTITIES:
            assert e.short_name in labels


# ── hr_urgency_kb ──────────────────────────────────────────────────


class TestHrUrgencyKb:
    def test_has_urgency_options(self):
        from app.domain.content import HR_REQUEST_URGENCY_OPTIONS

        data = _parse(hr_urgency_kb())
        labels = _labels(data)
        for opt in HR_REQUEST_URGENCY_OPTIONS:
            assert opt in labels


# ── hr_confirm_kb ──────────────────────────────────────────────────


class TestHrConfirmKb:
    def test_has_confirm_button(self):
        data = _parse(hr_confirm_kb())
        assert CMD_HR_CONFIRM in _payloads(data)

    def test_has_restart_button(self):
        data = _parse(hr_confirm_kb())
        assert CMD_HR_RESTART in _payloads(data)

    def test_confirm_is_positive(self):
        data = _parse(hr_confirm_kb())
        confirm_btn = [
            btn for btn in _all_buttons(data)
            if btn["action"]["payload"] == CMD_HR_CONFIRM
        ]
        assert len(confirm_btn) == 1
        assert confirm_btn[0]["color"] == "positive"


# ── hr_done_kb ─────────────────────────────────────────────────────


class TestHrDoneKb:
    def test_has_home_button(self):
        data = _parse(hr_done_kb())
        assert CMD_HOME in _payloads(data)

    def test_has_new_request_button(self):
        data = _parse(hr_done_kb())
        labels = _labels(data)
        assert _has_label(labels, "Новое обращение")
