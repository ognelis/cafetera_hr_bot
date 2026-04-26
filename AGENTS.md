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
Settings use inheritance: `CoreSettings` (shared RAG, storage, LLM config) → `AdminSettings` (adds `admin_api_key`) / `VKSettings` (adds `vk_access_token`, `vk_group_id`). Each uses `model_config = {"extra": "ignore"}` to share `.env` files. See `packages/*/src/*/config.py`.

- Never hardcode secrets — load via `pydantic-settings` from environment variables
- Provide `.env.example` with placeholders only; never commit real secrets
- Redact secrets from logs, traces, and debug output
- Use `secrets.compare_digest()` for constant-time comparison of webhook tokens
- Keep production and development secrets separate

Reference: `.qoder/rules/09-security.md`

## Architecture
Packages: `packages/core` (shared RAG, storage, domain) → `packages/admin` (FastAPI admin UI) / `packages/vk_bot` (VK bot).

Core layers: `cafetera_core/rag` (retrieval/prompts/chains), `cafetera_core/domain` (services), `cafetera_core/storage` (DB + S3).
Admin: `cafetera_admin/api` (routes), `cafetera_admin/domain` (admin-specific services).
VK Bot: `cafetera_vk_bot/handlers/` (message handlers), `cafetera_vk_bot/domain/` (VK-specific content/entities).

- Keep transport, business logic, and RAG pipeline separated
- FastAPI endpoints stay thin and delegate to services
- Shared logic for Telegram and VK lives in domain services in `packages/core`
- Prefer modular files over monolithic architecture
- New shared logic goes into `packages/core`. Package-specific logic stays in its package.

Reference: `.qoder/rules/00-architecture.md`

## Resource Safety & Lifespan
Use `build_resources()` / `close_resources()` from `cafetera_core.resources` for all resource lifecycle.
Reference: `.qoder/rules/08-resource-safety.md`

## Security & Webhooks
Validate all webhook secrets with `secrets.compare_digest()`. Never log secrets or full payloads.
Reference: `.qoder/rules/07-bot-apis.md`, `.qoder/rules/09-security.md`

## Document Upload & Ingestion
Upload → S3/MinIO storage + PostgreSQL metadata → background Docling parsing → chunk → embed → Qdrant.
Reference: `.qoder/rules/10-doc-upload.md`

## Frontend & Admin UI
HTMX + Alpine.js + Tailwind v4 + DaisyUI v5. No build pipeline. Vendor libs in `static/vendor/`.
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
- `uv sync` — install all workspace packages and dependencies before running tests.
- `uv run pytest` — run tests relevant to changed code.
  - `asyncio_mode = "auto"` — async tests run without extra decorators
- `uv run ruff check .` — linting with rules E/F/I/UP/B, line-length 100
- `uv run mypy packages/` — type checking with `strict = false`, `warn_unused_ignores = true`
- `uv run python -c 'import cafetera_core; import cafetera_admin; import cafetera_vk_bot'` — catch import errors early
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
