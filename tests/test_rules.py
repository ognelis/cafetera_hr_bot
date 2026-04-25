"""Tests for app.integrations.vk.rules — custom payload matching rules."""

import json
from unittest.mock import MagicMock

import pytest

from cafetera_vk_bot.rules import PayloadCmdRule


def _make_message(payload: dict | None = None) -> MagicMock:
    msg = MagicMock()
    msg.payload = json.dumps(payload) if payload is not None else None
    return msg


class TestPayloadCmdRule:
    @pytest.mark.asyncio
    async def test_matches_correct_cmd(self):
        rule = PayloadCmdRule("hire_entity")
        msg = _make_message({"cmd": "hire_entity", "entity": 1})
        result = await rule.check(msg)
        assert result is not False
        assert result["payload_data"]["cmd"] == "hire_entity"
        assert result["payload_data"]["entity"] == 1

    @pytest.mark.asyncio
    async def test_rejects_wrong_cmd(self):
        rule = PayloadCmdRule("hire_entity")
        msg = _make_message({"cmd": "fire_entity", "entity": 1})
        result = await rule.check(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_rejects_no_payload(self):
        rule = PayloadCmdRule("hire_entity")
        msg = _make_message(None)
        result = await rule.check(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_rejects_invalid_json(self):
        rule = PayloadCmdRule("hire_entity")
        msg = MagicMock()
        msg.payload = "not json"
        result = await rule.check(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_rejects_non_dict_payload(self):
        rule = PayloadCmdRule("test")
        msg = MagicMock()
        msg.payload = json.dumps([1, 2, 3])
        result = await rule.check(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_rejects_missing_cmd_key(self):
        rule = PayloadCmdRule("test")
        msg = _make_message({"action": "test"})
        result = await rule.check(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_full_payload_data(self):
        rule = PayloadCmdRule("vac_template")
        msg = _make_message({"cmd": "vac_template", "entity": 3, "extra": "data"})
        result = await rule.check(msg)
        assert result["payload_data"] == {"cmd": "vac_template", "entity": 3, "extra": "data"}
