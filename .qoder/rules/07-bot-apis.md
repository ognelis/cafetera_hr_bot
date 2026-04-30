---
trigger: glob
glob: packages/vk_bot/src/cafetera_vk_bot/**/*.py, packages/admin/src/cafetera_admin/api/*webhook*.py
---
# Bot API Integration Guidelines

## Telegram — aiogram 3.x

### Reference

For detailed Telegram Bot API method signatures beyond those shown above,
consult the official Telegram Bot API documentation.

### Rules
- Use aiogram 3.x (not 2.x). Import paths, types, and patterns differ significantly.
- Use `Bot` and `Dispatcher` from `aiogram`; `DefaultBotProperties` for global config.
- Register handlers via `@dp.message(...)` decorators; respond with `await message.answer(...)`.

### Production: webhook mode
Key steps: set webhook in lifespan (`bot.set_webhook()` with `secret_token` and `allowed_updates=dp.resolve_used_update_types()`), validate `X-Telegram-Bot-Api-Secret-Token` header with `secrets.compare_digest`, parse payload with `Update.model_validate(data, context={"bot": bot})`, feed to dispatcher (`await dp.feed_update(bot, update)`), delete webhook + close session on teardown. See `08-resource-safety.md` for lifespan teardown.

### Local development: polling mode
Run `scripts/polling.py`: delete webhook, then `dp.start_polling(bot)`.

### Do not
- Do not use aiogram 2.x patterns: executor, on_startup, on_shutdown.
- Do not parse Update manually without `Update.model_validate`.
- Do not block the event loop inside aiogram handlers.
- Do not compare secret tokens with `!=` — use `secrets.compare_digest` (timing-safe).

***

## VK — vkbottle 4.x

### Reference

For VK API method documentation, consult the official VK developer portal.

### Rules
- Use vkbottle 4.x. Register handlers via `@bot.on.message(...)` decorators.

### Production: Callback API mode
Key steps: create `BotCallback(url=..., secret_key=...)`, initialize `Bot(token=..., callback=callback)`, call `await bot.setup_webhook()` in lifespan startup, validate incoming `secret` field with `secrets.compare_digest`, return `confirmation_token` for confirmation events, process event as FastAPI `BackgroundTask` (`background_tasks.add_task(bot.process_event, data)`), return `PlainTextResponse("ok")`. No explicit Bot close method — webhook deregistration via VK admin panel or re-registration on next deploy.

### Local development: Long Poll mode
Run `scripts/polling_vk.py`: `bot.run_forever()` with `loop_wrapper.on_startup`/`on_shutdown`.

### Handler registration order
Handler labelers are registered in order: `start`, `ask`, `hire`, `fire`, `vacation`, `pay`, `sections`, `fallback`.
Order matters — vkbottle checks handlers top-to-bottom. `fallback` must be last.

### State management
Use vkbottle `BuiltinStateDispenser` for conversation state tracking in multi-step flows.
State is in-memory and does not persist across restarts.

### Resource initialization in polling mode
Use `loop_wrapper.on_startup` / `on_shutdown` to register async setup and cleanup coroutines:
```python
bot.loop_wrapper.on_startup.append(_setup(bot))
bot.loop_wrapper.on_shutdown.append(_cleanup(bot))
bot.run_forever()
```
Note: append already-called coroutines (not coroutine functions) to `on_startup`/`on_shutdown`.

### Do not
- Do not block the response with heavy handler logic in Callback mode — use background tasks.
- Do not skip `secret` validation on incoming events in Callback mode.

***

## RAG service integration via RAGClient

Bot handlers do **not** contain local RAG logic. They communicate with the RAG
microservice over HTTP using `RAGClient` from `cafetera_core.rag_client`.

### Injection pattern (polling mode)
```python
# In polling.py _setup:
res = await build_resources(settings, with_s3=True, with_db=True)
set_rag_client(res.rag_client)
set_system_prompt(SYSTEM_PROMPT)
```

### Query pattern (inside handlers)
```python
answer = await get_rag_client().ask(
    question,
    system_prompt=get_system_prompt(),
    category=category,
    include_metadata=True,
)
# Or streaming:
async for token in get_rag_client().stream_ask(question, system_prompt=..., category=...):
    ...
```

### Error handling
- If `RAGClient` is `None` at startup, log a warning and disable QA features gracefully.
- Wrap RAG calls in try/except — `httpx.HTTPStatusError` or `httpx.ConnectError` indicate service unavailability.
- Send a user-friendly message (e.g., "Service temporarily unavailable") when the RAG service cannot be reached.

### Do not
- Do not import RAG chain, retriever, or LLM directly in bot handlers.
- Do not initialize `RAGClient` per-request — use the shared instance from `Holder`.

***

## General rules (both adapters)

- Use webhook in production, polling only for local development — see `09-security.md`.
- Resource lifecycle (Bot init, teardown, session.close) → see `08-resource-safety.md`.
- Do not create new Bot instances per request.
- Do not put RAG or domain service logic directly inside bot handlers — pass normalized DTOs to domain services.
- Telegram and VK handlers must normalize incoming events into shared domain DTOs.
- Keep adapter-specific code strictly inside its package: VK bot in `packages/vk_bot/`, Telegram in `packages/admin/` (Post-MVP).
- Do not duplicate answer formatting logic — it belongs in the adapter layer, not in RAG or domain services.
- When in doubt about library API signatures, refer to the documentation links above before generating code.
- Do not invent undocumented API fields or response shapes.
