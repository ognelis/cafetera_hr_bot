"""Tests for app.integrations.vk.keyboards — keyboard builders."""

import json

import pytest
from vkbottle import Keyboard

from app.integrations.vk.keyboards import (
    CMD_ASK,
    CMD_CONTACT_HR,
    CMD_FIRE,
    CMD_HIRE,
    CMD_HOME,
    CMD_PAY,
    CMD_PROBATION,
    CMD_SICK,
    CMD_VACATION,
    main_menu_kb,
    stub_kb,
    with_service_row,
)


def _parse(kb: Keyboard) -> dict:
    return json.loads(kb.get_json())


def _all_buttons(data: dict) -> list[dict]:
    """Flatten all buttons from all rows."""
    return [btn for row in data["buttons"] for btn in row]


def _labels(data: dict) -> list[str]:
    return [btn["action"]["label"] for btn in _all_buttons(data)]


def _payloads(data: dict) -> list[dict]:
    """Payloads are already dicts after json.loads on the whole keyboard."""
    return [btn["action"]["payload"] for btn in _all_buttons(data)]


def _has_label(labels: list[str], substring: str) -> bool:
    return any(substring in label for label in labels)


# ── main_menu_kb ───────────────────────────────────────────────────


class TestMainMenuKb:
    def test_has_five_rows(self):
        data = _parse(main_menu_kb())
        assert len(data["buttons"]) == 5

    def test_seven_section_buttons_plus_contact_hr(self):
        data = _parse(main_menu_kb())
        # 7 section buttons + 1 contact HR = 8 total
        assert len(_all_buttons(data)) == 8

    def test_all_seven_sections_present(self):
        expected_payloads = [
            CMD_HIRE, CMD_FIRE, CMD_VACATION, CMD_PAY,
            CMD_SICK, CMD_PROBATION, CMD_ASK,
        ]
        data = _parse(main_menu_kb())
        payloads = _payloads(data)
        for p in expected_payloads:
            assert p in payloads, f"Missing payload {p}"

    def test_contact_hr_in_last_row(self):
        data = _parse(main_menu_kb())
        last_row = data["buttons"][-1]
        assert len(last_row) == 1
        assert last_row[0]["action"]["payload"] == CMD_CONTACT_HR

    def test_contact_hr_color_positive(self):
        data = _parse(main_menu_kb())
        last_btn = data["buttons"][-1][0]
        assert last_btn["color"] == "positive"

    def test_not_inline_not_one_time(self):
        data = _parse(main_menu_kb())
        assert data.get("one_time") is False
        assert data.get("inline") is False

    def test_first_row_has_hire_and_fire(self):
        data = _parse(main_menu_kb())
        first_row_payloads = [
            btn["action"]["payload"] for btn in data["buttons"][0]
        ]
        assert CMD_HIRE in first_row_payloads
        assert CMD_FIRE in first_row_payloads


# ── with_service_row ───────────────────────────────────────────────


class TestWithServiceRow:
    def test_adds_home_and_hr_by_default(self):
        kb = Keyboard(one_time=False, inline=False)
        with_service_row(kb)
        data = _parse(kb)
        labels = _labels(data)
        assert _has_label(labels, "Главное меню")
        assert _has_label(labels, "Написать в HR")

    def test_no_back_by_default(self):
        kb = Keyboard(one_time=False, inline=False)
        with_service_row(kb)
        data = _parse(kb)
        labels = _labels(data)
        assert not _has_label(labels, "Назад")

    def test_back_shown_when_payload_given(self):
        kb = Keyboard(one_time=False, inline=False)
        with_service_row(kb, back_payload=CMD_HOME)
        data = _parse(kb)
        labels = _labels(data)
        assert _has_label(labels, "Назад")

    def test_back_payload_matches(self):
        target = {"cmd": "some_section"}
        kb = Keyboard(one_time=False, inline=False)
        with_service_row(kb, back_payload=target)
        data = _parse(kb)
        back_btn = [
            btn for btn in _all_buttons(data)
            if "Назад" in btn["action"]["label"]
        ]
        assert len(back_btn) == 1
        assert back_btn[0]["action"]["payload"] == target

    def test_hide_home(self):
        kb = Keyboard(one_time=False, inline=False)
        with_service_row(kb, show_home=False)
        data = _parse(kb)
        labels = _labels(data)
        assert not _has_label(labels, "Главное меню")

    def test_hide_hr(self):
        kb = Keyboard(one_time=False, inline=False)
        with_service_row(kb, show_hr=False)
        data = _parse(kb)
        labels = _labels(data)
        assert not _has_label(labels, "Написать в HR")

    def test_returns_same_keyboard(self):
        kb = Keyboard(one_time=False, inline=False)
        result = with_service_row(kb)
        assert result is kb


# ── stub_kb ────────────────────────────────────────────────────────


class TestStubKb:
    def test_without_back_has_home_and_hr(self):
        data = _parse(stub_kb())
        labels = _labels(data)
        assert _has_label(labels, "Главное меню")
        assert _has_label(labels, "Написать в HR")
        assert not _has_label(labels, "Назад")

    def test_with_back_has_three_buttons(self):
        data = _parse(stub_kb(back_payload=CMD_HOME))
        buttons = _all_buttons(data)
        assert len(buttons) == 3

    def test_not_inline(self):
        data = _parse(stub_kb())
        assert data.get("inline") is False


# ── payload constants consistency ──────────────────────────────────


class TestPayloadConstants:
    @pytest.mark.parametrize("payload", [
        CMD_HOME, CMD_CONTACT_HR, CMD_HIRE, CMD_FIRE,
        CMD_VACATION, CMD_PAY, CMD_SICK, CMD_PROBATION, CMD_ASK,
    ])
    def test_payload_has_cmd_key(self, payload):
        assert "cmd" in payload
        assert isinstance(payload["cmd"], str)

    def test_all_cmd_values_unique(self):
        all_cmds = [
            CMD_HOME, CMD_CONTACT_HR, CMD_HIRE, CMD_FIRE,
            CMD_VACATION, CMD_PAY, CMD_SICK, CMD_PROBATION, CMD_ASK,
        ]
        values = [p["cmd"] for p in all_cmds]
        assert len(values) == len(set(values)), "Duplicate cmd values found"
