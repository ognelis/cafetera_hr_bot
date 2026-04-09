"""Tests for app.integrations.vk.states — BotStates enum."""

from vkbottle import BaseStateGroup

from app.integrations.vk.states import BotStates


class TestBotStates:
    def test_is_base_state_group(self):
        assert issubclass(BotStates, BaseStateGroup)

    def test_all_values_unique(self):
        values = [s.value for s in BotStates]
        assert len(values) == len(set(values)), "Duplicate state values"
