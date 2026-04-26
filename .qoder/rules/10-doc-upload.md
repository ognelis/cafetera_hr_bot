---
trigger: glob
glob: packages/admin/src/cafetera_admin/api/documents*.py, packages/core/src/cafetera_core/storage/**/*.py, templates/**/*.html, static/**/*.js
---
# Document Upload — API and Storage

Frontend stack (HTMX, Alpine.js, Jinja2, general patterns) → see `11-frontend.md`.

***

## Storage stack

Document upload uses two independent layers. Do not mix them.

| Layer | What it stores | Backend |
|---|---|---|
| **File storage** | Raw binary files (PDF, DOCX, XLSX) | MinIO (local) / S3 (production) |
| **Metadata / job status** | document_id, filename, status, timestamps | PostgreSQL via `databases[asyncpg]` |

***

## File storage — MinIO

MinIO is the only file storage backend. The project `docker-compose.yml` already contains the MinIO service definition — do not duplicate it.

Start MinIO: `docker compose up -d minio`

The same `aiobotocore` code works locally and in production — only `s3_endpoint_url` and credentials change via settings in `cafetera_core/config.py`.

Use `S3Storage` async wrapper around `aiobotocore` in `cafetera_core/storage/s3.py`. Initialize once in lifespan. Core methods: `upload()`, `download()`, `delete()`, `exists()`. Lazy connection with auto bucket creation.

***

## Metadata storage — PostgreSQL

Use PostgreSQL with `databases[asyncpg]` for job status and document metadata. Schema is auto-created on startup. Both local development and production use PostgreSQL.

Two tables in PostgreSQL via `databases[asyncpg]`:
- `documents` — document_id, filename, title, s3_key, mime_type, size_bytes, status, is_search_enabled, error, timestamps, chunk_count.
- `category_files` — file_id, category, subcategory, entity_id, filename, s3_key, mime_type, size_bytes, timestamps. Unique constraint on (category, subcategory, entity_id).

Settings: `database_url` in `cafetera_core/config.py`.

***

## Upload flow (states per file)

```
idle → uploading → pending → ingesting → indexed
                                       ↘ failed
```

- **uploading** — XHR in progress, show byte-level progress bar.
- **pending** — file received, background task queued.
- **ingesting** — chunking, embedding, writing to Qdrant.
- **indexed** — available for retrieval.
- **failed** — show error reason and Retry button.

***

## API

- POST `/documents/upload` accepts `UploadFile`, validates, reads content in handler (not in background task), creates job, triggers background ingestion.
- GET `/documents/{id}/status` returns JSON. HTMX partials at `/partials/document-status/{id}` for polling.
- Stop polling by returning the partial without `hx-trigger` when status is terminal.

***

## Validation

```python
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
```

Validate extension, MIME type, and file size in `validate_upload()`. Do not trust client-provided MIME type as the only validation.

Security details → see `09-security.md` (Files and uploads section).

***

## Document parsing

The project uses **Docling** (`langchain-docling` + `docling`) for advanced document parsing:
- Supports DOCX, XLSX, and PDF formats.
- Handles tables, headers, and structured content extraction.
- Docling ML models are pre-downloaded during Docker build to avoid runtime network calls.

***

## Ingestion task

Background ingestion: update status to `ingesting`, upload to S3, parse with Docling, chunk, embed, index to Qdrant, update status to `indexed` or `failed`.

***

## UX rules

- Show a per-file row: filename, size, progress bar, status badge.
- Never use a single global progress bar for multi-file uploads.
- On `failed`, show the error reason and a **Retry** button.
- On `indexed`, show a **Delete from index** action.
- Provide an empty state: "No documents indexed yet. Upload your first file."
- Allow both drag-and-drop and click-to-browse.
- Upload progress uses `XMLHttpRequest` (not `fetch`). Implementation in `static/js/upload.js`.
- Status polling uses HTMX `hx-trigger="every 2s"` with `hx-swap="outerHTML"` on the status partial.

***

## Do not

- Do not duplicate MinIO service config — it lives in `docker-compose.yml`.
- Do not read `UploadFile` inside the background task — read it in the handler first.
- Do not store uploaded files on the local filesystem — use MinIO.
- Do not trust client-provided MIME type as the only validation.
- Do not block the HTTP response waiting for ingestion to complete.
- Do not use a single global status for multi-file uploads.
- Do not use `fetch()` for upload progress — use `XMLHttpRequest`.
- Do not hardcode MinIO credentials — load from settings via `pydantic-settings`.
- Do not create a new `S3Storage` instance per request — initialize once in lifespan.

Reference: https://docs.python.org/3/library/asyncio.html
