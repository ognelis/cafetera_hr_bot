---
trigger: always_on
---
# Resource Safety

## General rules

- Always use async context managers or lifespan hooks for resource initialization
  and teardown.
- Never create long-lived clients (HTTP, Qdrant, LLM) inside request handlers —
  initialize them once in lifespan.
- Always close clients and connections on application shutdown.
- Do not leave unclosed aiohttp sessions, httpx clients, or qdrant connections.
- Prefer dependency injection via `app.state` or FastAPI `Depends` for shared resources.
- Prefer `asynccontextmanager` for wrapping resource lifecycle in reusable blocks.

---

## FastAPI lifespan

- Use FastAPI `lifespan` for all startup and shutdown logic.
- Do not use deprecated `on_event("startup")` / `on_event("shutdown")`.
- Initialize all shared resources (bot, vectorstore, retriever, HTTP clients)
  inside `lifespan` and attach to `app.state`.
- Always yield inside lifespan — teardown code must be after `yield`.

### Canonical pattern
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.state.http_client = httpx.AsyncClient()
    app.state.qdrant_client = QdrantClient(url=settings.qdrant_url)
    app.state.vectorstore = build_vectorstore(app.state.qdrant_client)
    yield
    # teardown
    await app.state.http_client.aclose()
    app.state.qdrant_client.close()

app = FastAPI(lifespan=lifespan)
```

---

## HTTP clients

- Always use `httpx.AsyncClient` for async HTTP calls — do not use `requests`.
- Never create `httpx.AsyncClient()` inside a single request handler.
- Always close `AsyncClient` on shutdown with `await client.aclose()`.
- Set reasonable timeouts on all outgoing HTTP requests.

### Canonical pattern
```python
client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
# on shutdown:
await client.aclose()
```

---

## Qdrant client

- Initialize `QdrantClient` once in lifespan, not per-request.
- Close `QdrantClient` on shutdown with `client.close()`.
- Do not share mutable Qdrant state between concurrent requests without isolation.

---

## aiogram Bot

- Always delete webhook on application shutdown via `await bot.delete_webhook()`.
- Always close bot session on shutdown via `await bot.session.close()`.

### Canonical teardown
```python
yield
await bot.delete_webhook()
await bot.session.close()
```

---

## vkbottle Bot

- Initialize `BotCallback` and `Bot` once in lifespan.
- Use `background_tasks` for event processing — never block the response.
- Do not create a new Bot instance per request.

---

## General async rules

- Do not use `time.sleep()` — use `await asyncio.sleep()`.
- Do not run blocking I/O inside async functions — use `asyncio.to_thread()` if needed.
- Do not share non-thread-safe state between concurrent coroutines without locks.
- Always await all coroutines — do not fire-and-forget unless explicitly intended.

---

## Do not

- Do not initialize clients at module level outside of lifespan unless they are
  stateless and cheap to create.
- Do not ignore exceptions during resource teardown — log them explicitly.
- Do not create new DB or vector store connections per request.
- Do not skip client.close() / session.close() calls on shutdown.