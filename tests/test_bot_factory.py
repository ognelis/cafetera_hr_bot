"""Tests for app.integrations.vk.bot — bot factory and handler wiring."""

from app.config import Settings
from app.integrations.vk.bot import _HANDLER_LABELERS, create_bot
from app.integrations.vk.handlers import (
    ask,
    fallback,
    fire,
    get_state_dispenser,
    hire,
    pay,
    sections,
    start,
    vacation,
)


class TestHandlerLabelerOrder:
    """Fallback must be last — it matches every message."""

    def test_fallback_is_last(self):
        assert _HANDLER_LABELERS[-1] is fallback.bl

    def test_start_is_first(self):
        assert _HANDLER_LABELERS[0] is start.bl

    def test_sections_before_fallback(self):
        idx_sections = _HANDLER_LABELERS.index(sections.bl)
        idx_fallback = _HANDLER_LABELERS.index(fallback.bl)
        assert idx_sections < idx_fallback

    def test_hire_fire_vacation_registered(self):
        assert hire.bl in _HANDLER_LABELERS
        assert fire.bl in _HANDLER_LABELERS
        assert vacation.bl in _HANDLER_LABELERS

    def test_pay_ask_registered(self):
        assert pay.bl in _HANDLER_LABELERS
        assert ask.bl in _HANDLER_LABELERS

    def test_ask_before_fallback(self):
        idx_ask = _HANDLER_LABELERS.index(ask.bl)
        idx_fallback = _HANDLER_LABELERS.index(fallback.bl)
        assert idx_ask < idx_fallback


class TestCreateBot:
    def test_returns_bot_instance(self):
        settings = Settings(vk_access_token="test_token_placeholder", _env_file=None)
        bot = create_bot(settings)
        from vkbottle import Bot
        assert isinstance(bot, Bot)

    def test_handlers_registered(self):
        settings = Settings(vk_access_token="test_token_placeholder", _env_file=None)
        bot = create_bot(settings)
        handler_count = len(bot.labeler.message_view.handlers)
        # start: 2 (on_start, on_home)
        # ask: 2 (on_ask, on_ask_text)
        # hire: 5 (hire, hire_entity, checklist, contract, onboarding)
        # fire: 6 (fire, fire_resignation, fire_resignation_entity, checklist, bypass, grounds)
        # vacation: 6 (vacation, select, type, template, rag, schedule)
        # pay: 3 (on_pay, on_pay_overtime, on_pay_bonus)
        # sections: 2 (sick, probation)
        # fallback: 1 (on_fallback)
        assert handler_count == 27

    def test_token_forwarded_to_bot(self):
        """Verify test placeholder token is used, not a real one (09-security)."""
        token = "test_token_placeholder"
        settings = Settings(vk_access_token=token, _env_file=None)
        bot = create_bot(settings)
        assert bot.api.token_generator.token == token

    def test_state_dispenser_shared(self):
        settings = Settings(vk_access_token="test_token_placeholder", _env_file=None)
        bot = create_bot(settings)
        assert bot.state_dispenser is get_state_dispenser()
