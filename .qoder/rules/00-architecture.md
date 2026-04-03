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
- Do not place retrieval, prompt building, or vector DB logic in webhook handlers.
- Prefer modular files over a monolithic bot.py architecture.
- New features must be added by module and layer, not by appending to one large file.

## Layer boundaries
- `app/api` handles HTTP and webhook transport only.
- `app/domain` contains business use cases and service logic.
- `app/rag` contains retrieval, prompts, chains, citation helpers, and vector search code.
- `app/integrations` contains provider-specific adapters and clients.
- `scripts` contains ingestion, reindex, and maintenance scripts.
- `tests` contains unit, integration, and e2e tests.

## Do not
- Do not duplicate RAG logic between Telegram and VK.
- Do not call external providers directly from route handlers unless it is transport-specific.
- Do not mix configuration loading with business logic.