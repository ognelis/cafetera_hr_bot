"""Custom vkbottle rules for partial payload matching."""

from __future__ import annotations

import json

from vkbottle import ABCRule
from vkbottle.bot import Message


class PayloadCmdRule(ABCRule[Message]):
    """Match messages whose JSON payload has ``{"cmd": <expected>}``.

    Returns ``{"payload_data": <full_payload_dict>}`` so the handler can
    access extra fields (e.g. ``entity``) via keyword argument.
    """

    def __init__(self, cmd: str) -> None:
        self.cmd = cmd

    async def check(self, event: Message) -> dict | bool:
        if not event.payload:
            return False
        try:
            payload = json.loads(event.payload)
        except (json.JSONDecodeError, TypeError):
            return False
        if isinstance(payload, dict) and payload.get("cmd") == self.cmd:
            return {"payload_data": payload}
        return False
