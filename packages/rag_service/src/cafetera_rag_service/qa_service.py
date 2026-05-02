"""Domain QA service — wraps the RAG chain for use by transport handlers.

The QAService class is initialized with qdrant client, embeddings, llm,
and settings. Chains are built dynamically per query. Handlers call service
methods which always return a displayable string, even on error.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import Runnable
    from qdrant_client import AsyncQdrantClient

    from cafetera_rag_service.config import RagServiceSettings
    from cafetera_rag_service.rag.reranker import HttpRerankerClient

logger = logging.getLogger(__name__)

ERR_NO_ANSWER = (
    "\U0001f50d К сожалению, точного ответа не найдено.\n\n"
    "Рекомендуем обратиться в HR-отдел компании."
)

ERR_DOCUMENT_UNAVAILABLE = (
    "\u26a0\ufe0f Не удалось получить ответ.\n\n"
    "Пожалуйста, задайте вопрос позже."
)

VK_MSG_LIMIT = 4096
_TRUNCATION_SUFFIX = "\n\n…Обратитесь в HR-отдел для полной информации."
_CUT_AT = VK_MSG_LIMIT - len(_TRUNCATION_SUFFIX)


def _truncate(text: str, limit: int = VK_MSG_LIMIT) -> str:
    """Truncate *text* to fit VK message length limit."""
    if len(text) <= limit:
        return text
    cut = text[:_CUT_AT]
    # cut at last space to avoid splitting a word
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut + _TRUNCATION_SUFFIX


class QAService:
    """QA service that holds RAG chain and related resources.

    Initialized with qdrant client, embeddings, llm, and settings.
    Builds RAG chains dynamically per query.
    """

    def __init__(
        self,
        *,
        qdrant_client: AsyncQdrantClient | None = None,
        embeddings: Embeddings | None = None,
        llm: BaseChatModel | None = None,
        settings: RagServiceSettings | None = None,
        global_system_prompt: str | None = None,
        include_metadata: bool = False,
        sparse_embedding: object | None = None,
        reranker: HttpRerankerClient | None = None,
    ) -> None:
        self._qdrant_client = qdrant_client
        self._embeddings = embeddings
        self._llm = llm
        self._settings = settings
        self._global_system_prompt = global_system_prompt
        self._include_metadata = include_metadata
        self._sparse_embedding = sparse_embedding
        self._reranker = reranker

    def _build_document_chain(self, document_id: str) -> Runnable | None:
        """Build a RAG chain scoped to a specific document.

        Returns the chain if QA is initialized, or None otherwise.
        """
        if (
            self._qdrant_client is None
            or self._settings is None
            or self._embeddings is None
            or self._llm is None
        ):
            return None

        from cafetera_rag_service.rag.chain import build_rag_chain
        from cafetera_rag_service.rag.prompts import DOCUMENT_EXPERTS_PROMPT
        from cafetera_rag_service.rag.retriever import build_retriever_for_document

        retriever = build_retriever_for_document(
            self._settings,
            document_id,
            qdrant_client=self._qdrant_client,
            embeddings=self._embeddings,
            collection_name=self._settings.qdrant_collection,
            k=self._settings.doc_query_k,
            sparse_embedding=self._sparse_embedding,
        )
        return build_rag_chain(
            retriever,
            self._llm,
            system_prompt=DOCUMENT_EXPERTS_PROMPT,
            include_metadata=self._include_metadata,
            reranker=self._reranker,
        )

    def _build_global_chain(self, k: int = 4, category: str | None = None) -> Runnable | None:
        """Build a global RAG chain with the specified k value.

        Returns the chain if QA is initialized with required resources,
        or None otherwise.
        """
        if (
            self._qdrant_client is None
            or self._settings is None
            or self._embeddings is None
            or self._llm is None
        ):
            return None

        from cafetera_rag_service.rag.chain import build_rag_chain
        from cafetera_rag_service.rag.prompts import CATEGORY_HINTS
        from cafetera_rag_service.rag.retriever import build_retriever

        retriever = build_retriever(
            self._settings,
            qdrant_client=self._qdrant_client,
            embeddings=self._embeddings,
            collection_name=self._settings.qdrant_collection,
            k=k,
            sparse_embedding=self._sparse_embedding,
        )
        category_hint = CATEGORY_HINTS.get(category) if category else None
        return build_rag_chain(
            retriever,
            self._llm,
            system_prompt=self._global_system_prompt,
            include_metadata=self._include_metadata,
            category_hint=category_hint,
            reranker=self._reranker,
        )

    async def ask(self, question: str, category: str | None = None) -> str:
        """Query the RAG chain and return a displayable answer string.

        Uses adaptive k based on question complexity.

        * If the chain was not initialised -> ``ERR_NO_ANSWER``.
        * If the chain raises at runtime -> ``ERR_DOCUMENT_UNAVAILABLE``.
        * Long answers are truncated to fit the VK message limit.
        """
        from cafetera_rag_service.rag.retriever import estimate_k

        k = estimate_k(
            question,
            max_k=self._settings.global_max_k if self._settings else 10,
        )
        chain = self._build_global_chain(k, category=category)
        if chain is None:
            return ERR_NO_ANSWER

        try:
            answer: str = await chain.ainvoke(question)
        except Exception:
            logger.error("RAG chain failed for question: %s", question, exc_info=True)
            return ERR_DOCUMENT_UNAVAILABLE

        if not answer or not answer.strip():
            return ERR_NO_ANSWER

        return _truncate(answer.strip())

    async def ask_about_document(self, question: str, document_id: str) -> str:
        """Query the RAG chain scoped to a specific document.

        * If the QA service was not initialised -> ``ERR_NO_ANSWER``.
        * If the chain raises at runtime -> ``ERR_DOCUMENT_UNAVAILABLE``.
        * Long answers are truncated to fit the VK message limit.
        """
        chain = self._build_document_chain(document_id)
        if chain is None:
            return ERR_NO_ANSWER

        try:
            answer: str = await chain.ainvoke(question)
        except Exception:
            logger.error(
                "RAG chain failed for document %s question: %s",
                document_id,
                question,
                exc_info=True,
            )
            return ERR_DOCUMENT_UNAVAILABLE

        if not answer or not answer.strip():
            return ERR_NO_ANSWER

        return _truncate(answer.strip())

    async def ask_with_contexts(
        self, question: str, category: str | None = None,
    ) -> tuple[str, list[str]]:
        """Return (answer, retrieved_contexts) for evaluation purposes."""
        from cafetera_rag_service.rag.retriever import build_retriever, estimate_k

        if (
            self._qdrant_client is None
            or self._settings is None
            or self._embeddings is None
            or self._llm is None
        ):
            return ERR_NO_ANSWER, []

        k = estimate_k(
            question,
            max_k=self._settings.global_max_k if self._settings else 10,
        )
        chain = self._build_global_chain(k, category=category)
        if chain is None:
            return ERR_NO_ANSWER, []

        retriever = build_retriever(
            self._settings,
            qdrant_client=self._qdrant_client,
            embeddings=self._embeddings,
            collection_name=self._settings.qdrant_collection,
            k=k,
            sparse_embedding=self._sparse_embedding,
        )

        try:
            docs = await retriever.ainvoke(question)
            contexts = [doc.page_content for doc in docs]
        except Exception:
            logger.error(
                "Retriever failed for question: %s", question, exc_info=True,
            )
            contexts = []

        try:
            answer: str = await chain.ainvoke(question)
        except Exception:
            logger.error(
                "RAG chain failed for question: %s", question, exc_info=True,
            )
            return ERR_DOCUMENT_UNAVAILABLE, contexts

        if not answer or not answer.strip():
            return ERR_NO_ANSWER, contexts

        return answer.strip(), contexts

    async def stream_ask(self, question: str, category: str | None = None):
        """Stream tokens from the global RAG chain.

        Uses adaptive k based on question complexity.
        Yields each token string as it arrives from the LLM.
        """
        from cafetera_rag_service.rag.retriever import estimate_k

        k = estimate_k(
            question,
            max_k=self._settings.global_max_k if self._settings else 10,
        )
        chain = self._build_global_chain(k, category=category)
        if chain is None:
            yield ERR_NO_ANSWER
            return

        try:
            async for token in chain.astream(question):
                if isinstance(token, str):
                    yield token
                elif hasattr(token, "content"):
                    yield str(token.content)
                else:
                    yield str(token)
        except asyncio.CancelledError:
            logger.info("Streaming cancelled for global question: %s", question)
            raise
        except Exception:
            logger.error(
                "RAG chain streaming failed for global question: %s",
                question,
                exc_info=True,
            )
            yield ERR_DOCUMENT_UNAVAILABLE

    async def stream_about_document(self, question: str, document_id: str):
        """Stream tokens from the RAG chain scoped to a specific document.

        Yields each token string as it arrives from the LLM.
        Handles errors gracefully by yielding an error message.
        """
        chain = self._build_document_chain(document_id)
        if chain is None:
            yield ERR_NO_ANSWER
            return

        try:
            async for token in chain.astream(question):
                if isinstance(token, str):
                    yield token
                elif hasattr(token, "content"):
                    yield str(token.content)
                else:
                    yield str(token)
        except asyncio.CancelledError:
            logger.info(
                "Streaming cancelled for document %s question: %s", document_id, question
            )
            raise
        except Exception:
            logger.error(
                "RAG chain streaming failed for document %s question: %s",
                document_id,
                question,
                exc_info=True,
            )
            yield ERR_DOCUMENT_UNAVAILABLE

    def close(self) -> None:
        """Release references held by the QA service."""
        self._qdrant_client = None
        self._settings = None
        self._embeddings = None
        self._llm = None
        self._sparse_embedding = None
        self._reranker = None
