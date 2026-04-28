"""Pydantic request/response schemas for the RAG service API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    category: str | None = None
    system_prompt: str
    include_metadata: bool = False


class AskResponse(BaseModel):
    answer: str


class AskDocumentRequest(BaseModel):
    question: str
    document_id: str


class ChunkData(BaseModel):
    text: str
    metadata: dict[str, Any] = {}


class IndexChunksRequest(BaseModel):
    document_id: str
    filename: str
    chunks: list[ChunkData]
    is_search_enabled: bool = True


class IndexChunksResponse(BaseModel):
    status: str = "ok"
    chunks_indexed: int


class InvalidateCacheRequest(BaseModel):
    document_id: str | None = None


class ToggleSearchRequest(BaseModel):
    is_search_enabled: bool


class StatusResponse(BaseModel):
    status: str = "ok"


class IngestRequest(BaseModel):
    document_id: str
    filename: str
    s3_key: str
    is_search_enabled: bool = True


class IngestResponse(BaseModel):
    status: str = "ok"
    chunks_indexed: int


class HealthResponse(BaseModel):
    status: str
    qdrant: str
    llm: str
