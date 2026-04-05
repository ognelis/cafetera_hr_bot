"""Tests for app.config — Settings loading."""

from app.config import Settings


class TestSettingsDefaults:
    def test_default_token_is_empty(self):
        settings = Settings(vk_access_token="")
        assert settings.vk_access_token == ""

    def test_default_group_id_is_zero(self):
        settings = Settings(vk_access_token="tok")
        assert settings.vk_group_id == 0


class TestSettingsFromEnv:
    def test_reads_token_from_env(self, monkeypatch):
        monkeypatch.setenv("VK_ACCESS_TOKEN", "env_test_token")
        monkeypatch.setenv("VK_GROUP_ID", "42")
        settings = Settings()
        assert settings.vk_access_token == "env_test_token"
        assert settings.vk_group_id == 42

    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv("VK_ACCESS_TOKEN", "override")
        settings = Settings()
        assert settings.vk_access_token == "override"
