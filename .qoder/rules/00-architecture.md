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
- New shared logic goes into `packages/core`. Package-specific logic stays in its package.

## Package structure
- `packages/core/src/cafetera_core/` — shared foundation (storage, domain services, config, RAG HTTP client).
- `packages/rag_service/src/cafetera_rag_service/` — RAG HTTP microservice (retrieval, chains, parsing, indexing, QA service).
- `packages/admin/src/cafetera_admin/` — FastAPI admin UI, document parsing, admin-specific services.
- `packages/vk_bot/src/cafetera_vk_bot/` — VK bot handlers, keyboards, VK-specific domain.
- `scripts/` — entry point wrappers (admin_server.py, rag_server.py, polling_vk.py).
- `templates/` — Jinja2 templates for admin UI.
- `static/` — frontend assets (CSS, JS, vendor libraries).
- `tests/` — unit, integration, and e2e tests.

## Layer boundaries (within packages)
- `cafetera_core/domain/` — shared business use cases (CategoryFileService).
- `cafetera_core/rag_client.py` — HTTP client for communicating with the RAG service.
- `cafetera_rag_service/rag/` — retrieval, prompts, chains, embeddings, vector search.
- `cafetera_rag_service/qa_service.py` — QA service (question answering over RAG pipeline).
- `cafetera_rag_service/parser.py` — document parsing and chunking for ingestion.
- `cafetera_core/storage/` — PostgreSQL repositories, S3/MinIO client.
- `cafetera_admin/api/` — HTTP routes and admin transport.
- `cafetera_admin/domain/` — admin-specific services (DocumentService).
- `cafetera_vk_bot/handlers/` — VK message handlers (transport adapters).
- `cafetera_vk_bot/domain/` — VK-specific content, entities, topic hints.

## Do not
- Do not duplicate RAG logic between Telegram and VK adapters.
- Do not mix configuration loading with business logic.