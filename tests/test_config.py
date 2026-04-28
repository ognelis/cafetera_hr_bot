"""Tests for cafetera_vk_bot.config — VKSettings loading."""

from cafetera_vk_bot.config import VKSettings


class TestSettingsDefaults:
    def test_default_token_is_empty(self):
        settings = VKSettings(vk_access_token="", _env_file=None)
        assert settings.vk_access_token == ""

    def test_default_group_id_is_zero(self):
        settings = VKSettings(vk_access_token="tok", _env_file=None)
        assert settings.vk_group_id == 0


class TestSettingsFromEnv:
    def test_reads_token_from_env(self, monkeypatch):
        monkeypatch.setenv("VK_ACCESS_TOKEN", "env_test_token")
        monkeypatch.setenv("VK_GROUP_ID", "42")
        settings = VKSettings()
        assert settings.vk_access_token == "env_test_token"
        assert settings.vk_group_id == 42

    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv("VK_ACCESS_TOKEN", "override")
        settings = VKSettings()
        assert settings.vk_access_token == "override"


# ── Package import smoke test ─────────────────────────────────────


def test_all_packages_importable():
    """Verify all workspace packages can be imported without errors."""
    import cafetera_admin
    import cafetera_core
    import cafetera_rag_service
    import cafetera_vk_bot

    assert cafetera_core is not None
    assert cafetera_admin is not None
    assert cafetera_vk_bot is not None
    assert cafetera_rag_service is not None
