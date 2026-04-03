---
trigger: always_on
---
# Architecture

## Goal
Keep the codebase modular, testable, and easy for agentic development.

## Rules
- Keep transport, business logic, and RAG pipeline separated.
- FastAPI endpoints must stay thin and delegate to services.
- Telegram and VK integrations are transport adapters only.
- Shared logic for Telegram and VK must live in domain services.
- Prefer modular files over a monolithic bot.py architecture.
- New features must be added by module and layer, not by appending to one large file.

## Layer boundaries
- `app/api` — HTTP and webhook transport only.
- `app/domain` — business use cases and service logic.
- `app/rag` — retrieval, prompts, chains, citation helpers, and vector search.
- `app/integrations` — provider-specific adapters and clients.
- `scripts` — ingestion, reindex, and maintenance scripts.
- `tests` — unit, integration, and e2e tests.

## Do not
- Do not duplicate RAG logic between Telegram and VK adapters.
- Do not mix configuration loading with business logic.