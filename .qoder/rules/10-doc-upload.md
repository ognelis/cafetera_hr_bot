---
trigger: glob
glob: app/api/upload*.py, app/api/documents*.py, app/domain/ingestion*.py, app/storage/**/*.py, app/templates/**/*.html, app/static/**/*.js, scripts/ingest*.py
---
# Document Upload — API and Storage

Frontend stack (HTMX, Alpine.js, Jinja2, general patterns) → see `11-frontend.md`.

***

## Storage stack

Document upload uses two independent layers. Do not mix them.

| Layer | What it stores | Local dev | Production |
|---|---|---|---|
| **File storage** | Raw binary files (PDF, DOCX, TXT) | MinIO via Docker | S3, GCS, or MinIO |
| **Metadata / job status** | job_id, filename, status, timestamps | SQLite | PostgreSQL |

***

## File storage — MinIO

MinIO is the only file storage backend. The project `docker-compose.yml` already
contains the MinIO service definition — do not duplicate it here.

Start MinIO: `docker compose up -d minio`

The same `aiobotocore` code works locally and in production —
only `s3_endpoint_url` and credentials change via settings.

### Settings
```python
class Settings(BaseSettings):
    s3_endpoint_url: str        # http://localhost:9000 locally; empty for AWS S3
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "rag-documents"
    max_upload_size_bytes: int = 20 * 1024 * 1024  # 20 MB
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt", ".md"]
```

### S3Storage client
```python
# app/storage/s3.py
import aiobotocore.session

class S3Storage:
    def __init__(self, settings):
        self._settings = settings

    def _client(self):
        session = aiobotocore.session.get_session()
        return session.create_client(
            "s3",
            endpoint_url=self._settings.s3_endpoint_url or None,
            aws_access_key_id=self._settings.s3_access_key,
            aws_secret_access_key=self._settings.s3_secret_key,
            region_name="us-east-1",
        )

    async def upload(self, key: str, content: bytes, content_type: str) -> str:
        async with self._client() as client:
            await client.put_object(
                Bucket=self._settings.s3_bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        return key

    async def delete(self, key: str) -> None:
        async with self._client() as client:
            await client.delete_object(
                Bucket=self._settings.s3_bucket,
                Key=key,
            )

    async def generate_presigned_url(self, key: str, expires: int = 3600) -> str:
        async with self._client() as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._settings.s3_bucket, "Key": key},
                ExpiresIn=expires,
            )
```

Initialize once in lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.storage = S3Storage(settings)
    yield
```

***

## Metadata storage — SQLite

Use SQLite with `aiosqlite` for job status and document metadata.
Add Alembic when schema stabilizes. Switch to PostgreSQL in production.

```python
# app/storage/db.py
import aiosqlite
from pathlib import Path

DB_PATH = Path("data/documents.db")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    job_id      TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    s3_key      TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE)
        await db.commit()

async def upsert_job(job_id: str, **fields) -> None:
    # aiosqlite.execute() runs a single statement — use two separate calls.
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO documents (job_id) VALUES (:job_id)",
            {"job_id": job_id},
        )
        if fields:
            set_clause = ", ".join(f"{k} = :{k}" for k in fields)
            await db.execute(
                f"UPDATE documents SET {set_clause}, updated_at = datetime('now') "
                f"WHERE job_id = :job_id",
                {"job_id": job_id, **fields},
            )
        await db.commit()

async def get_job(job_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM documents WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
```

Add `data/` to `.gitignore`.

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

### Upload endpoint
```python
@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    validate_upload(file)
    content = await file.read()      # must read before background task
    job_id = str(uuid4())
    await upsert_job(job_id, filename=file.filename, status="pending")
    background_tasks.add_task(
        ingest_document,
        job_id, file.filename, content,
        request.app.state.storage,
    )
    return UploadResponse(job_id=job_id, filename=file.filename, status="pending")
```

### Status endpoint
```python
@router.get("/documents/{job_id}/status", response_model=StatusResponse)
async def get_document_status(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return StatusResponse(**job)
```

### Status partial endpoint (for HTMX polling)
```python
@router.get("/documents/{job_id}/status-partial")
async def get_document_status_partial(job_id: str, request: Request):
    """Returns an HTML fragment for HTMX polling. Different from /status (JSON)."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return templates.TemplateResponse(
        "partials/job_status.html",
        {"request": request, "job": job},
    )
```

### List endpoint
```python
@router.get("/documents", response_model=list[DocumentMeta])
async def list_documents():
    ...
```

***

## Upload UI patterns

### XHR with progress (use instead of fetch)
```javascript
function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/documents/upload');
    xhr.upload.onprogress = e => {
        if (e.lengthComputable)
            updateProgress(file.name, Math.round(e.loaded / e.total * 100));
    };
    xhr.onload = () => {
        if (xhr.status === 200) {
            const { job_id } = JSON.parse(xhr.responseText);
            pollStatus(file.name, job_id);
        } else {
            setFileState(file.name, 'failed', parseError(xhr));
        }
    };
    xhr.onerror = () => setFileState(file.name, 'failed', 'Network error');
    setFileState(file.name, 'uploading');
    xhr.send(formData);
}
```

### Status polling via HTMX
```html
<div
  id="job-{{ job_id }}"
  hx-get="/api/documents/{{ job_id }}/status-partial"
  hx-trigger="every 2s"
  hx-swap="outerHTML">
  <span class="badge badge--pending">Processing…</span>
</div>
```

Stop polling by returning the partial without `hx-trigger` when status is terminal.

### UX rules
- Show a per-file row: filename, size, progress bar, status badge.
- Never use a single global progress bar for multi-file uploads.
- On `failed`, show the error reason and a **Retry** button.
- On `indexed`, show a **Delete from index** action.
- Provide an empty state: "No documents indexed yet. Upload your first file."
- Allow both drag-and-drop and click-to-browse.

***

## Validation

```python
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

def validate_upload(file: UploadFile) -> None:
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(422, f"File type '{ext}' is not supported.")
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(422, "MIME type not allowed.")
    if file.size and file.size > settings.max_upload_size_bytes:
        raise HTTPException(413, "File exceeds size limit.")
```

Security details → see `09-security.md` (Files and uploads section).

***

## Ingestion task
```python
async def ingest_document(
    job_id: str,
    filename: str,
    content: bytes,
    storage: S3Storage,
) -> None:
    try:
        await upsert_job(job_id, status="ingesting")
        s3_key = f"documents/{job_id}/{filename}"
        await storage.upload(s3_key, content, detect_mime(filename))
        docs = load_and_split(filename, content)
        await index_documents(docs)
        await upsert_job(job_id, status="indexed", s3_key=s3_key)
    except Exception as e:
        await upsert_job(job_id, status="failed", error=str(e))
        logger.exception("Ingestion failed for job %s", job_id)
```

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
- Do not store file binaries in SQLite — SQLite holds metadata only.
- Do not create a new `S3Storage` instance per request — initialize once in lifespan.
- Do not pass multiple SQL statements to a single `aiosqlite.execute()` call — only the first runs.