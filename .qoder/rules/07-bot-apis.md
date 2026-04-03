---
trigger: glob
glob: app/integrations/telegram/**/*.py, app/api/telegram_webhook.py,   app/integrations/vk/**/*.py, app/api/vk_webhook.py, app/core/lifecycle.py
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
- Register webhook in FastAPI lifespan using `bot.set_webhook()`.
- Delete webhook in lifespan teardown using `bot.delete_webhook()`.
- Parse incoming payload with `Update.model_validate(data, context={"bot": bot})`.
- Feed parsed update to dispatcher with `await dp.feed_update(bot, update)`.
- Register message handlers on Dispatcher using `@dp.message(...)` decorators.
- Use `dp.resolve_used_update_types()` when calling `set_webhook` to limit update types.
- Respond to users via `await message.answer(...)` inside handlers.
- Do not use polling mode in production.

### Canonical webhook pattern
```python
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update
from fastapi import FastAPI, Request

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

@app.post("/api/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if x_telegram_bot_api_secret_token != settings.telegram_secret_token:
        raise HTTPException(status_code=403)
    update = Update.model_validate(
        await request.json(), context={"bot": bot}
    )
    await dp.feed_update(bot, update)
```

### Do not
- Do not use aiogram 2.x patterns: executor, on_startup, on_shutdown.
- Do not parse Update manually without `Update.model_validate`.
- Do not block the event loop inside aiogram handlers.
- Do not put RAG or domain service logic directly inside aiogram handlers.

---

## VK — vkbottle 4.x

### Reference
- Official vkbottle documentation: https://vkbottle.rtfd.io
- Callback API tutorial: https://vkbottle.readthedocs.io/ru/latest/tutorial/callback-bot/
- Low-level Callback API reference: https://vkbottle.readthedocs.io/ru/v4.x/low-level/callback/callback/
- VK API methods reference: https://dev.vk.com/en/method

### Rules
- Use vkbottle 4.x.
- For production, use Callback API mode via `BotCallback` from `vkbottle.callback`.
- Initialize bot with `Bot(token=TOKEN, callback=callback)`.
- Register event handlers on Bot using `@bot.on.message(...)` decorators.
- Pass incoming request body to `await bot.process_event(data)`.
- Run `process_event` as a FastAPI `BackgroundTask` to keep response time short.
- Always validate `secret` field in incoming VK events before processing.
- Return VK confirmation token on `type == "confirmation"` events.
- Return plain text `"ok"` for all other successfully received events.

### Canonical webhook pattern
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

### Do not
- Do not use Long Poll API in production.
- Do not block the response with heavy handler logic — use background tasks.
- Do not skip `secret` validation on incoming events.
- Do not put RAG or domain service logic directly inside vkbottle handlers.

---

## General rules (both adapters)

- Telegram and VK handlers must normalize incoming events into shared domain DTOs.
- Pass normalized DTOs to shared domain services — never call RAG logic directly
  from bot handlers.
- Keep adapter-specific code strictly inside:
  - `app/integrations/telegram/`
  - `app/integrations/vk/`
- Do not duplicate answer formatting logic — it belongs in the adapter layer,
  not in RAG or domain services.
- When in doubt about library API signatures or behavior, refer to the
  documentation links listed above before generating code.
- Do not invent undocumented API fields or response shapes.