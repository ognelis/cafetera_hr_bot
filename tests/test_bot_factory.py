"""Tests for app.integrations.vk.bot — bot factory and handler wiring."""

from app.config import Settings
from app.integrations.vk.bot import _HANDLER_LABELERS, create_bot
from app.integrations.vk.handlers import fallback, sections, start


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


class TestCreateBot:
    def test_returns_bot_instance(self):
        settings = Settings(vk_access_token="test_token_placeholder")
        bot = create_bot(settings)
        from vkbottle import Bot
        assert isinstance(bot, Bot)

    def test_handlers_registered(self):
        settings = Settings(vk_access_token="test_token_placeholder")
        bot = create_bot(settings)
        handler_count = len(bot.labeler.message_view.handlers)
        # start: 3 handlers (on_start, on_home, on_contact_hr)
        # sections: 7 handlers (hire, fire, vacation, pay, sick, probation, ask)
        # fallback: 1 handler (on_fallback)
        assert handler_count == 11

    def test_token_forwarded_to_bot(self):
        """Verify test placeholder token is used, not a real one (09-security)."""
        token = "test_token_placeholder"
        settings = Settings(vk_access_token=token)
        bot = create_bot(settings)
        assert bot.api.token_generator.token == token
