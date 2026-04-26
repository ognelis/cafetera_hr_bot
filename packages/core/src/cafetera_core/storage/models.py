"""Document metadata model for the storage layer."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(StrEnum):
    """Processing status of an ingested document."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    stale = "stale"


class DocumentRecord(BaseModel):
    """Metadata record for a single document stored in the knowledge base."""

    id: int
    document_id: str
    filename: str
    title: str
    s3_key: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus = DocumentStatus.pending
    is_search_enabled: bool = Field(default=True)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None = None
    chunk_count: int = 0
    indexing_config: dict[str, Any] | None = None
