"""Cross-encoder reranking module using sentence-transformers CrossEncoder."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Wraps sentence-transformers CrossEncoder for document reranking."""

    def __init__(self, model_name: str, top_n: int) -> None:
        self._model = CrossEncoder(model_name, trust_remote_code=True)
        self._top_n = top_n

    def rerank(
        self, query: str, documents: list[Document]
    ) -> list[Document]:
        """Rerank documents synchronously and return top_n results."""
        if not documents:
            return []
        pairs = [(query, doc.page_content) for doc in documents]
        scores = self._model.predict(pairs)
        scored = sorted(
            enumerate(scores), key=lambda x: float(x[1]), reverse=True
        )
        return [documents[idx] for idx, _ in scored[: self._top_n]]

    async def arerank(
        self, query: str, documents: list[Document]
    ) -> list[Document]:
        """Rerank documents asynchronously via thread pool."""
        if not documents:
            return []
        pairs = [(query, doc.page_content) for doc in documents]
        scores = await asyncio.to_thread(self._model.predict, pairs)
        scored = sorted(
            enumerate(scores), key=lambda x: float(x[1]), reverse=True
        )
        return [documents[idx] for idx, _ in scored[: self._top_n]]


class RerankingRetriever(BaseRetriever):
    """LangChain retriever that composes a base retriever with reranking."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_retriever: BaseRetriever
    reranker: CrossEncoderReranker

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
