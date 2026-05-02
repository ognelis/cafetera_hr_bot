"""Thin async HTTP client for the RAG microservice."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class RAGClient:
    """HTTP client for the Cafetera RAG service."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 60.0,
        index_timeout: float = 300.0,
    ) -> None:
        headers = {"X-API-Key": api_key} if api_key else {}
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout),
        )
        self._index_timeout = index_timeout

    async def ask(
        self,
        question: str,
        *,
        system_prompt: str,
        category: str | None = None,
        include_metadata: bool = False,
    ) -> str:
        resp = await self._client.post(
            "/api/qa/ask",
            json={
                "question": question,
                "category": category,
                "system_prompt": system_prompt,
                "include_metadata": include_metadata,
            },
        )
        resp.raise_for_status()
        return resp.json()["answer"]

    async def stream_ask(
        self,
        question: str,
        *,
        system_prompt: str,
        category: str | None = None,
        include_metadata: bool = False,
    ) -> AsyncIterator[str]:
        async with self._client.stream(
            "POST",
            "/api/qa/stream",
            json={
                "question": question,
                "category": category,
                "system_prompt": system_prompt,
                "include_metadata": include_metadata,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    try:
                        yield json.loads(payload)["token"]
                    except (json.JSONDecodeError, KeyError):
                        pass

    async def ask_about_document(
        self, question: str, document_id: str
    ) -> str:
        resp = await self._client.post(
            "/api/qa/ask-document",
            json={"question": question, "document_id": document_id},
        )
        resp.raise_for_status()
        return resp.json()["answer"]

    async def stream_about_document(
        self, question: str, document_id: str
    ) -> AsyncIterator[str]:
        async with self._client.stream(
            "POST",
            "/api/qa/stream-document",
            json={"question": question, "document_id": document_id},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    try:
                        yield json.loads(payload)["token"]
                    except (json.JSONDecodeError, KeyError):
                        pass

    async def index_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: list[dict[str, Any]],
        *,
        is_search_enabled: bool = True,
    ) -> int:
        resp = await self._client.post(
            "/api/index/chunks",
            json={
                "document_id": document_id,
                "filename": filename,
                "chunks": chunks,
                "is_search_enabled": is_search_enabled,
            },
            timeout=httpx.Timeout(self._index_timeout),
        )
        resp.raise_for_status()
        return resp.json()["chunks_indexed"]

    async def ingest_document(
        self,
        document_id: str,
        filename: str,
        s3_key: str,
        *,
        is_search_enabled: bool = True,
    ) -> dict[str, Any]:
        """Send a document for full ingestion (parse + embed + index).

        The RAG service handles: S3 download -> Docling parse -> chunk ->
        embed -> index to Qdrant.  Old chunks for the same document_id
        are deleted automatically.

        Returns a dict with keys: ``chunks_indexed``, ``page_count``,
        ``binary_hash``, ``extracted_title``, ``status``.
        """
        resp = await self._client.post(
            "/api/index/ingest",
            json={
                "document_id": document_id,
                "filename": filename,
                "s3_key": s3_key,
                "is_search_enabled": is_search_enabled,
            },
            timeout=httpx.Timeout(600.0),
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "chunks_indexed": data["chunks_indexed"],
            "page_count": data.get("page_count"),
            "binary_hash": data.get("binary_hash"),
            "extracted_title": data.get("extracted_title"),
            "status": data.get("status"),
        }

    async def toggle_search(
        self,
        document_id: str,
        *,
        is_search_enabled: bool,
    ) -> None:
        """Update is_search_enabled flag on all Qdrant chunks for a document."""
        resp = await self._client.patch(
            f"/api/index/documents/{document_id}/search",
            json={"is_search_enabled": is_search_enabled},
        )
        resp.raise_for_status()

    async def delete_document(self, document_id: str) -> None:
        resp = await self._client.delete(f"/api/index/documents/{document_id}")
        resp.raise_for_status()

    async def health(self) -> dict[str, str]:
        resp = await self._client.get("/api/health")
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()
