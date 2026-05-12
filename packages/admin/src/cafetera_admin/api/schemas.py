"""Pydantic response models and TypedDicts for admin API endpoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from pydantic import BaseModel

# ── Document responses ────────────────────────────────────────────


class DocumentResponse(BaseModel):
    """JSON-safe representation of a DocumentRecord."""

    document_id: str
    filename: str
    title: str
    s3_key: str
    mime_type: str
    size_bytes: int
    size_human: str
    status: str
    is_search_enabled: bool
    error: str | None
    created_at: str
    updated_at: str
    indexed_at: str | None
    chunk_count: int
    indexing_config: dict[str, Any] | None = None


class DocumentTableContext(TypedDict):
    """Template context for the document table partial."""

    documents: list[DocumentResponse]
    human_size: Callable[[int], str]
    page: int
    per_page: int
    pages: int
    total: int
    search: str | None
    date_from: str | None
    date_to: str | None
    status_filter: str
    source_type_filter: str
    sort_field: str
    sort_dir: str


# ── Category file responses ──────────────────────────────────────


class CategoryFileResponse(BaseModel):
    """JSON-safe representation of a CategoryFileRecord."""

    file_id: str
    category: str
    subcategory: str
    entity_id: int
    filename: str
    s3_key: str
    mime_type: str
    size_bytes: int
    size_human: str
    created_at: str
    updated_at: str


class EntityInfo(BaseModel):
    """Short entity info for slot listing."""

    id: int
    name: str
    short_name: str


class CategoryListResponse(BaseModel):
    """Response for the category slots + entities listing endpoint."""

    categories: dict[str, Any]
    entities: list[EntityInfo]
