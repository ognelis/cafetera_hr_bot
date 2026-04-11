# AGENTS.md

## Goal
This repository uses agentic coding for implementation assistance, but architecture, invariants, and acceptance are human-led.

## Stack
- Python 3.13. Package manager: `uv` only — never pip or poetry.
- FastAPI + pydantic v2 + pydantic-settings.
- **Primary channel: VK** — vkbottle 4.x. Telegram (aiogram 3.x) is Post-MVP.
- RAG: LangChain + Qdrant.
- ASGI server: Hypercorn.
- HTTP client: `httpx.AsyncClient` only — never `requests` or bare `aiohttp`.
- File uploads: `python-multipart`.
- Database: `databases[asyncpg]` for PostgreSQL in prod and locally.
- Run commands via `uv run` (e.g. `uv run pytest`, `uv run uvicorn ...`).

## Prod vs local
- **Local dev:** polling — `uv run python scripts/polling_vk.py` (VK), `uv run python scripts/polling.py` (Telegram, Post-MVP).
- **Production:** webhook via FastAPI lifespan — never use polling in production.

## Secrets & Configuration
All secrets via `pydantic-settings`. Canonical fields for this project:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # VK (primary)
    vk_access_token: str
    vk_secret: str
    vk_confirmation_token: str
    vk_webhook_url: str

    # Telegram (Post-MVP)
    telegram_bot_token: str
    telegram_secret_token: str
    telegram_webhook_url: str

    # RAG
    qdrant_url: str
    qdrant_api_key: str | None = None
    llm_api_key: str

    # Storage
    s3_endpoint_url: str          # http://localhost:9000 locally; empty for AWS S3
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "rag-documents"
```

- Never hardcode secrets — load via `pydantic-settings` from environment variables
- Provide `.env.example` with placeholders only; never commit real secrets
- Redact secrets from logs, traces, and debug output
- Use `secrets.compare_digest()` for constant-time comparison of webhook tokens
- Keep production and development secrets separate

Reference: `.qoder/rules/09-security.md`

## Architecture
Layers: `app/api` (transport) → `app/domain` (services) → `app/rag` (retrieval/prompts).
Storage: `app/storage` — S3/MinIO client and DB access (separate from domain logic).
Adapters: `app/integrations/telegram/`, `app/integrations/vk/`.

- Keep transport, business logic, and RAG pipeline separated
- FastAPI endpoints stay thin and delegate to services
- Shared logic for Telegram and VK lives in domain services
- Prefer modular files over monolithic architecture

Reference: `.qoder/rules/00-architecture.md`

## Resource Safety & Lifespan
- Use FastAPI `lifespan` for all startup/shutdown logic (not deprecated `on_event`)
- Initialize all long-lived resources (HTTP clients, DB, LLM, bots) in lifespan, attach to `app.state`
- Always `yield` inside lifespan; teardown code runs after `yield`
- Close all clients on shutdown: `await client.aclose()`, `client.close()`, `await bot.session.close()`
- Prefer dependency injection via `app.state` or FastAPI `Depends`

Reference: `.qoder/rules/08-resource-safety.md`

## Security & Webhooks
- **Telegram:** Validate `X-Telegram-Bot-Api-Secret-Token` header with `secrets.compare_digest()`
- **VK:** Validate incoming `secret` field with `secrets.compare_digest()`
- Never log secrets, tokens, or full webhook payloads
- Add rate limiting on public endpoints and webhook-adjacent endpoints
- Protect chat endpoints from flooding and accidental loops
- Sanitize error responses — return generic messages externally, log details internally

Reference: `.qoder/rules/07-bot-apis.md`, `.qoder/rules/09-security.md`

## Document Upload & Ingestion
- **Storage:** S3/MinIO via `aiobotocore` for file storage; PostgreSQL via `databases` for metadata
- **Flow:** Upload → background task → chunk → embed → store in Qdrant
- **Validation:** Check file size, MIME type, and extension before processing
- **Status tracking:** `idle → uploading → pending → ingesting → indexed/failed`

Reference: `.qoder/rules/10-doc-upload.md`

## Frontend & Admin UI
- **HTMX** — server-driven interactivity; return HTML fragments, never JSON
- **Alpine.js** — local UI state only (dropzones, toggles, counters); not for server state
- **Tailwind CSS v4 + DaisyUI v5** — DaisyUI components first, Tailwind for layout/spacing
- **No build pipeline** — all libraries from `app/static/vendor/` directory (no CDN)
- **Admin UI style:** clean, calm, data-first enterprise design

Reference: `.qoder/rules/11-frontend.md`, `.qoder/rules/12-admin-ui-design.md`

## Core workflow
1. First inspect relevant files and existing patterns.
2. Then produce a short implementation plan.
3. Do not start coding until the plan is coherent with repository conventions.
4. Implement in small, reviewable changes.
5. After implementation, run validation commands.
6. Report what changed, what was verified, and what remains risky.

## Hard constraints
- Do not introduce new dependencies unless explicitly requested.
- Do not modify public contracts unless explicitly requested.
- Do not change database schema, infra config, or CI unless explicitly requested.
- Do not touch files outside the stated scope.
- Reuse existing patterns before inventing new abstractions.
- Prefer minimal diff over broad refactoring.
- Stop and ask if requirements conflict with codebase conventions.

## Code quality
- Follow existing architecture and naming.
- Prefer explicitness over cleverness.
- Keep functions small and readable.
- Add or update tests for any non-trivial behavior change.
- Preserve backward compatibility unless the task explicitly allows breaking changes.
- **Prefer functions over classes** — use classes only for stateful I/O adapters
- **Async patterns:** compose from small awaitable steps; use `TaskGroup`/`gather` only for independent I/O; no fire-and-forget `create_task()` unless supervised

Reference: `.qoder/rules/01-python-style.md`

## Validation
Before finishing, always:
- `uv run pytest` — run tests relevant to changed code.
  - `asyncio_mode = "auto"` — async tests run without extra decorators
- `uv run ruff check .` — linting with rules E/F/I/UP/B, line-length 100
- `uv run mypy app/` — type checking with `strict = false`, `warn_unused_ignores = true`
- `uv run python -c 'import app'` — catch import errors early
- Check for import errors and missing dependencies.
- Summarize: what passed, what failed, what was skipped and why.

Reference: `.qoder/rules/05-tests.md`

## Final response format
Return:
1. Files changed
2. Why each change was made
3. Validation performed
4. Remaining risks or assumptions

---

## Rule Files Reference

This file is a quick-start summary. For detailed patterns and canonical code examples, consult the rule files in `.qoder/rules/`:

| File | Description |
|------|-------------|
| `00-architecture.md` | Layer boundaries and modular design rules |
| `01-python-style.md` | Functions vs classes, async patterns, code style |
| `02-rag-guidelines.md` | RAG pipeline implementation guidance |
| `03-fastapi-api.md` | FastAPI endpoint patterns |
| `04-uv-workflow.md` | uv package manager workflow |
| `05-tests.md` | Testing patterns and priorities |
| `06-markdown-docs.md` | Documentation style guidelines |
| `07-bot-apis.md` | Telegram (aiogram) and VK (vkbottle) integration patterns |
| `08-resource-safety.md` | Lifespan, resource initialization, and teardown |
| `09-security.md` | Secrets, webhook validation, rate limiting |
| `10-doc-upload.md` | File upload, storage, and ingestion flow |
| `11-frontend.md` | HTMX, Alpine.js, Tailwind, DaisyUI patterns |
| `12-admin-ui-design.md` | Enterprise admin UI design direction |
| `13-python-uv-docker.md` | How to build Dockerfile |
