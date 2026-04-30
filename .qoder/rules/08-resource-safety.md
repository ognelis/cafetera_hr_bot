---
trigger: always_on
---
# Resource Safety

## General rules

- Initialize shared resources once in lifespan; close them on shutdown.
- Never create clients per-request; prefer dependency injection via `app.state`.
- See subsections below for specific resource patterns.

***

## FastAPI lifespan

- Use FastAPI `lifespan` for all startup and shutdown logic.
- Do not use deprecated `on_event("startup")` / `on_event("shutdown")`.
- Initialize all shared resources (bot, vectorstore, retriever, HTTP clients)
  inside `lifespan` and attach to `app.state`.
- Always yield inside lifespan — teardown code must be after `yield`.

### Canonical pattern (Admin)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from cafetera_core.resources import build_resources, close_resources

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    res = await build_resources(settings, with_s3=True, with_db=True)

    # Store individual resources in app.state for FastAPI deps
    app.state.rag_client = res.rag_client
    app.state.s3 = res.s3
    app.state.doc_repo = res.doc_repo
    app.state.category_file_service = res.category_file_service
    yield
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

***

## RAG Microservice Resources

The RAG service (`packages/rag_service`) uses its own resource container
separate from `AppResources` in core.

- `RagResources` dataclass holds: `qdrant_client`, `embeddings`, `llm`,
  `sparse_embeddings`, `reranker`, `s3_storage`.
- Factory: `build_rag_resources(settings)` / `close_rag_resources(res)` in
  `cafetera_rag_service.resources`.
- Helper: `build_qa_service(res, system_prompt)` creates a `QAService` from
  initialized resources. Raises `ValueError` if required resources are missing.

### Canonical pattern (RAG service)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.resources import build_rag_resources, close_rag_resources

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = RagServiceSettings()
    res = await build_rag_resources(settings)
    app.state.rag_resources = res
    app.state.settings = settings
    app.state.qa_services = {}  # cache: prompt -> QAService
    yield
    await close_rag_resources(res)
```

### Do not
- Do not use `AppResources` / `build_resources()` inside the RAG service — it has
  its own factory.
- Do not instantiate `QAService` per request — cache by system prompt hash.