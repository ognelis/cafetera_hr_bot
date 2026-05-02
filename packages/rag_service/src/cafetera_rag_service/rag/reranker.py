"""HTTP-based reranker client calling an external llama.cpp /v1/rerank endpoint."""

from __future__ import annotations

import asyncio
import logging

import httpx
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

logger = logging.getLogger(__name__)


class HttpRerankerClient:
    """Calls an external reranker service via HTTP POST to /v1/rerank."""

    def __init__(self, client: httpx.AsyncClient, top_n: int) -> None:
        self._client = client
        self._top_n = top_n

    def rerank(self, query: str, documents: list[Document]) -> list[Document]:
        """Rerank documents synchronously (delegates to async via thread)."""
        if not documents:
            return []
        return asyncio.run(self.arerank(query, documents))

    async def arerank(
        self, query: str, documents: list[Document]
    ) -> list[Document]:
        """Rerank documents by calling the external /v1/rerank endpoint."""
        if not documents:
            return []

        texts = [doc.page_content for doc in documents]
        payload = {
            "query": query,
            "documents": texts,
            "top_n": self._top_n,
        }

        try:
            response = await self._client.post("/v1/rerank", json=payload)
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Reranker HTTP request failed")
            return documents[: self._top_n]

        data = response.json()
        results = data.get("results", [])

        scored = sorted(
            results, key=lambda r: r.get("relevance_score", 0.0), reverse=True
        )
        reranked: list[Document] = []
        for item in scored[: self._top_n]:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(documents):
                reranked.append(documents[idx])

        return reranked


class RerankingRetriever(BaseRetriever):
    """LangChain retriever that composes a base retriever with reranking."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_retriever: BaseRetriever
    reranker: HttpRerankerClient

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        docs = self.base_retriever.invoke(query)
        return self.reranker.rerank(query, docs)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        docs = await self.base_retriever.ainvoke(query)
        return await self.reranker.arerank(query, docs)
