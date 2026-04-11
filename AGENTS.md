# AGENTS.md

## Goal
This repository uses agentic coding for implementation assistance, but architecture, invariants, and acceptance are human-led.

## Stack
- Python 3.13. Package manager: `uv` only — never pip or poetry.
- FastAPI + pydantic v2 + pydantic-settings.
- **Primary channel: VK** — vkbottle 4.x. Telegram (aiogram 3.x) is Post-MVP.
- RAG: LangChain + Qdrant.
- Frontend (admin UI): HTMX + Alpine.js + Jinja2 + **Tailwind CSS v4 + DaisyUI v5**. No build pipeline (no npm/webpack/Vite) — all from CDN.
- Storage: MinIO via `aiobotocore` (file storage); `aiosqlite` / SQLite → PostgreSQL in prod (job metadata).
- HTTP client: `httpx.AsyncClient` only — never `requests` or bare `aiohttp`.
- Run commands via `uv run` (e.g. `uv run pytest`, `uv run uvicorn ...`).

## Prod vs local
- **Local dev:** polling — `uv run python scripts/polling_vk.py` (VK), `uv run python scripts/polling.py` (Telegram, Post-MVP).
- **Production:** webhook via FastAPI lifespan — never use polling in production.

## Environment variables
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

Never hardcode any of these. Provide `.env.example` with placeholders only.

## Architecture
Layers: `app/api` (transport) → `app/domain` (services) → `app/rag` (retrieval/prompts).
Storage: `app/storage` — S3/MinIO client and DB access (separate from domain logic).
Adapters: `app/integrations/telegram/`, `app/integrations/vk/`.
Detailed layer rules: see `.qoder/rules/00-architecture.md`.

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

## Validation
Before finishing, always:
- `uv run pytest` — run tests relevant to changed code.
- `uv run ruff check .` — if ruff is configured.
- `uv run mypy app/` — if mypy is configured.
- Check for import errors and missing dependencies.
- Summarize: what passed, what failed, what was skipped and why.

## Final response format
Return:
1. Files changed
2. Why each change was made
3. Validation performed
4. Remaining risks or assumptions