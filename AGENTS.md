# AGENTS.md

## Goal
This repository uses agentic coding for implementation assistance, but architecture, invariants, and acceptance are human-led.

## Stack
- Python 3.13. Package manager: `uv` only — never pip or poetry. FastAPI + pydantic v2 + pydantic-settings.
- Primary channel: VK (vkbottle 4.x); Telegram Post-MVP (aiogram 3.x). RAG: LangChain + Qdrant. HTTP client: `httpx.AsyncClient` only.
- Production: webhook via FastAPI lifespan. Local dev: `uv run python scripts/polling_vk.py` (VK), `uv run python scripts/admin_server.py` (admin, port 8000), `uv run python scripts/rag_server.py` (RAG, port 8001).

Reference: `.qoder/rules/04-uv-workflow.md`, `.qoder/rules/07-bot-apis.md`

## Secrets & Configuration
Settings use inheritance: `CoreSettings` → `AdminSettings` / `VKSettings`. Each uses `model_config = {"extra": "ignore"}` to share `.env` files. See `packages/*/src/*/config.py`.

Reference: `.qoder/rules/09-security.md` for full security requirements.

## Architecture
Monorepo: `packages/core` → `packages/admin` / `packages/vk_bot` / `packages/rag_service`. Keep transport, business logic, and RAG pipeline separated. New shared logic goes into `packages/core`.

Reference: `.qoder/rules/00-architecture.md` for package structure and layer boundaries.

## Resource Safety & Lifespan
Use `build_resources()` / `close_resources()` from `cafetera_core.resources` for all resource lifecycle.
Reference: `.qoder/rules/08-resource-safety.md`

## Security & Webhooks
Validate all webhook secrets with `secrets.compare_digest()`. Never log secrets or full payloads.
Reference: `.qoder/rules/07-bot-apis.md`, `.qoder/rules/09-security.md`

## Document Upload & Ingestion
Upload → S3 + PostgreSQL → Docling parsing → chunk → embed → Qdrant. See `.qoder/rules/10-doc-upload.md`.

## Frontend & Admin UI
HTMX + Alpine.js + Tailwind v4 + DaisyUI v5. No build pipeline. See `.qoder/rules/11-frontend.md`, `.qoder/rules/12-admin-ui-design.md`.

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
- `uv run python -c 'import cafetera_core; import cafetera_admin; import cafetera_vk_bot; import cafetera_rag_service'` — catch import errors early
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
