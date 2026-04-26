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

***

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
from cafetera_core.resources import build_resources, close_resources

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — build all shared resources via factory
    res = await build_resources(settings, with_s3=True, with_db=True)
    app.state.qa_service = res.build_qa_service(SYSTEM_PROMPT)
    app.state.category_file_service = res.category_file_service
    yield
    # teardown — close all resources
    await close_resources(res)

app = FastAPI(lifespan=lifespan)
```

***

## HTTP clients

- Use `httpx.AsyncClient` only (never `requests`). Initialize once in lifespan, close on shutdown with `await client.aclose()`.
- Set reasonable timeouts on all outgoing HTTP requests.

***

## Qdrant client

- Initialize `QdrantClient` once in lifespan, not per-request.
- Close `QdrantClient` on shutdown with `client.close()`.
- Do not share mutable Qdrant state between concurrent requests without isolation.

***

## aiogram Bot

- aiogram `Bot`/`Dispatcher` are safe at module level. Set webhook in lifespan, delete webhook + close session on teardown.

***

## vkbottle Bot

- vkbottle `Bot` safe at module level. Use `loop_wrapper.on_startup`/`on_shutdown` for resource lifecycle in polling mode.
- In webhook mode: call `await bot.setup_webhook()` in lifespan startup; use `background_tasks` for event processing.

***

## General async rules

- Do not use `time.sleep()` — use `await asyncio.sleep()`.
- Do not run blocking I/O inside async functions — use `asyncio.to_thread()` if needed.
- Do not share non-thread-safe state between concurrent coroutines without locks.
- Always await all coroutines — do not fire-and-forget unless explicitly intended.

***

## Do not

- Do not initialize clients at module level outside of lifespan unless they are
  stateless configuration containers with no active connections.
- Do not ignore exceptions during resource teardown — log them explicitly.
- Do not create new DB or vector store connections per request.
- Do not skip client.close() / session.close() calls on shutdown.

Reference: https://fastapi.tiangolo.com/advanced/events/