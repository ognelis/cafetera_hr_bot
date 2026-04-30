---
trigger: glob
glob: packages/admin/src/cafetera_admin/**/*.py, packages/core/src/cafetera_core/config.py, packages/rag_service/src/cafetera_rag_service/api/**/*.py
---
# FastAPI API

## Rules
- Keep endpoints thin: validate input, call service, return response.
- Use pydantic schemas for API contracts.
- Put application settings in a dedicated settings module.
- Keep webhook endpoints idempotent where possible.
- Separate HTTP transport concerns from domain logic.

## Settings
- Use `pydantic-settings` for environment-based configuration.
- Read configuration from `.env` for local development.
- Settings use inheritance: `CoreSettings` (shared) is extended by `AdminSettings` and `VKSettings`. Each package imports its own settings class.

## Route design
- Use `/health` for health checks.
- Put application endpoints under `/api` when appropriate.
- Keep Telegram and VK webhook routes separate.
- Normalize incoming payloads before passing to domain services.
- Admin server entry point: `scripts/admin_server.py` → `cafetera_admin.server` (Hypercorn, port 8000).
- Use `AppResources` factory from `cafetera_core.resources` for resource initialization in lifespan.

## Do not
- Do not place business rules in routers.
- Do not return ad hoc JSON shapes if a schema already exists.

***

## RAG service API

The RAG service is a separate FastAPI application running on port 8001.
Entry point: `scripts/rag_server.py` → `cafetera_rag_service.server` (Hypercorn, port 8001).

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (Qdrant + LLM status). **No auth required.** |
| POST | `/api/qa/ask` | Ask a question via the RAG chain, return full answer. |
| POST | `/api/qa/stream` | Stream answer tokens as SSE events. |
| POST | `/api/qa/ask-document` | Ask a question about a specific document. |
| POST | `/api/qa/stream-document` | Stream answer tokens for a specific document (SSE). |
| POST | `/api/index/ingest` | Full ingestion pipeline: S3 download → parse → embed → index. |
| POST | `/api/index/chunks` | Embed and upsert pre-parsed chunks to Qdrant. |
| DELETE | `/api/index/documents/{document_id}` | Delete all chunks for a document from Qdrant. |
| PATCH | `/api/index/documents/{document_id}/search` | Toggle `is_search_enabled` for a document's chunks. |
| POST | `/api/index/cache/invalidate` | Clear QAService cached chains. |

### Authentication

- All endpoints except `/api/health` are protected by `X-API-Key` header.
- Auth dependency: `verify_api_key` in `cafetera_rag_service.api.deps`.
- Uses `secrets.compare_digest()` for constant-time comparison.
- When `rag_service_api_key` is empty, auth is skipped (development mode).

### Consumers

- Admin and VK bot communicate with the RAG service via `RAGClient` from `cafetera_core.rag_client`.
- Do not call RAG service endpoints directly from transport handlers — use `RAGClient`.

# Notes
- Lifespan, client initialization, and resource teardown → see `08-resource-safety.md`.
- Secret validation and security headers → see `09-security.md`.