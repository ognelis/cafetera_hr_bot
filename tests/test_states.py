"""Tests for app.integrations.vk.states — BotStates enum."""

from vkbottle import BaseStateGroup

from app.integrations.vk.states import BotStates


class TestBotStates:
    def test_is_base_state_group(self):
        assert issubclass(BotStates, BaseStateGroup)

    def test_has_six_hr_request_states(self):
        hr_states = [s for s in BotStates if s.value.startswith("hr_")]
        assert len(hr_states) == 6

    def test_all_values_unique(self):
        values = [s.value for s in BotStates]
        assert len(values) == len(set(values)), "Duplicate state values"

    def test_expected_states_present(self):
        names = {s.name for s in BotStates}
        expected = {
            "HR_REQUEST_NAME",
            "HR_REQUEST_TOPIC",
            "HR_REQUEST_DETAILS",
            "HR_REQUEST_ENTITY",
            "HR_REQUEST_URGENCY",
            "HR_REQUEST_CONFIRM",
        }
        assert expected.issubset(names)
