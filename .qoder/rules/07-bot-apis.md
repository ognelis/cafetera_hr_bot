---
trigger: glob
glob: app/integrations/telegram/**/*.py, app/api/telegram_webhook.py, app/integrations/vk/**/*.py, app/api/vk_webhook.py, app/core/lifecycle.py
---
# Bot API Integration Guidelines

## Telegram — aiogram 3.x

### Reference
- Official aiogram 3.x documentation: https://docs.aiogram.dev/en/latest/
- Webhook integration guide: https://docs.aiogram.dev/en/latest/dispatcher/webhook.html
- Telegram Bot API methods: https://core.telegram.org/bots/api#available-methods

### Rules
- Use aiogram 3.x (not 2.x). Import paths, types, and patterns differ significantly.
- Use `Bot` and `Dispatcher` from `aiogram` for core objects.
- Use `DefaultBotProperties` for global bot configuration (parse_mode, etc.).
- Register message handlers on Dispatcher using `@dp.message(...)` decorators.
- Respond to users via `await message.answer(...)` inside handlers.

### Production: webhook mode
- Register webhook in FastAPI lifespan using `bot.set_webhook()`.
- Delete webhook and close bot session in lifespan teardown — see `08-resource-safety.md`.
- Parse incoming payload with `Update.model_validate(data, context={"bot": bot})`.
- Feed parsed update to dispatcher with `await dp.feed_update(bot, update)`.
- Use `dp.resolve_used_update_types()` when calling `set_webhook` to limit update types.

#### Canonical webhook pattern
```python
import secrets
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(
        url=settings.telegram_webhook_url,
        secret_token=settings.telegram_secret_token,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    yield
    await bot.delete_webhook()
    await bot.session.close()

@app.post("/api/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # Use secrets.compare_digest to prevent timing attacks (see 09-security.md)
    if not secrets.compare_digest(
        x_telegram_bot_api_secret_token or "",
        settings.telegram_secret_token,
    ):
        raise HTTPException(status_code=403)
    update = Update.model_validate(
        await request.json(), context={"bot": bot}
    )
    await dp.feed_update(bot, update)
```

### Local development: polling mode
Run with: `uv run python scripts/polling.py`

#### Canonical polling pattern
```python
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()

# register handlers on dp here

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

### Do not
- Do not use aiogram 2.x patterns: executor, on_startup, on_shutdown.
- Do not parse Update manually without `Update.model_validate`.
- Do not block the event loop inside aiogram handlers.
- Do not compare secret tokens with `!=` — use `secrets.compare_digest` (timing-safe).

***

## VK — vkbottle 4.x

### Reference
- Official vkbottle documentation: https://vkbottle.readthedocs.io/en/latest/
- VK API methods reference: https://dev.vk.com/en/method

### Rules
- Use vkbottle 4.x.
- Register event handlers on Bot using `@bot.on.message(...)` decorators.

### Production: Callback API mode
- Use Callback API mode via `BotCallback` from `vkbottle.callback`.
- Initialize bot with `Bot(token=TOKEN, callback=callback)`.
- Pass incoming request body to `await bot.process_event(data)`.
- Run `process_event` as a FastAPI `BackgroundTask` to keep response time short.
- Always validate `secret` field in incoming VK events before processing.
- Return `confirmation_token` only for VK confirmation events.
- Return plain text `"ok"` for all other successfully received events.

#### Canonical webhook pattern
```python
from contextlib import asynccontextmanager
from vkbottle import Bot
from vkbottle.callback import BotCallback
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import PlainTextResponse

callback = BotCallback(
    url=settings.vk_webhook_url,
    title="rag-bot",
    secret_key=settings.vk_secret,
)
bot = Bot(token=settings.vk_access_token, callback=callback)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.setup_webhook()
    yield
    # vkbottle Bot has no explicit close method.
    # Webhook deregistration is handled via VK admin panel or re-registration on next deploy.

@app.post("/api/webhooks/vk")
async def vk_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if data.get("type") == "confirmation":
        return PlainTextResponse(settings.vk_confirmation_token)
    if data.get("secret") != settings.vk_secret:
        return PlainTextResponse("forbidden", status_code=403)
    background_tasks.add_task(bot.process_event, data)
    return PlainTextResponse("ok")
```

### Local development: Long Poll mode
Run with: `uv run python scripts/polling_vk.py`

#### Canonical polling pattern
```python
import asyncio
from vkbottle import Bot

bot = Bot(token=settings.vk_access_token)

# register handlers on bot here

async def main():
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
```

### Do not
- Do not block the response with heavy handler logic in Callback mode — use background tasks.
- Do not skip `secret` validation on incoming events in Callback mode.

***

## General rules (both adapters)

- **Use webhook in production, polling only for local development** — see `09-security.md`.
- Resource lifecycle (Bot init, teardown, session.close) → see `08-resource-safety.md`.
- Do not create new Bot instances per request.
- Do not put RAG or domain service logic directly inside bot handlers — pass normalized DTOs to domain services.
- Telegram and VK handlers must normalize incoming events into shared domain DTOs.
- Keep adapter-specific code strictly inside `app/integrations/telegram/` and `app/integrations/vk/`.
- Do not duplicate answer formatting logic — it belongs in the adapter layer, not in RAG or domain services.
- When in doubt about library API signatures, refer to the documentation links above before generating code.
- Do not invent undocumented API fields or response shapes.