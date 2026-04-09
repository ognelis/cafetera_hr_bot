"""Domain QA service — wraps the RAG chain for use by transport handlers.

The QAService class is initialized with chain, qdrant client, embeddings, llm,
and settings. Handlers call service methods which always return a displayable
string, even on error.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.domain.content import ERR_DOCUMENT_UNAVAILABLE, ERR_NO_ANSWER

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import Runnable
    from qdrant_client import QdrantClient

    from app.config import Settings

logger = logging.getLogger(__name__)

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

    Initialized with chain, qdrant client, embeddings, llm, and settings.
    Provides methods to query the RAG chain and manage resources.
    """

    def __init__(
        self,
        *,
        chain: Runnable | None = None,
        qdrant_client: QdrantClient | None = None,
        embeddings: Embeddings | None = None,
        llm: BaseChatModel | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._chain = chain
        self._qdrant_client = qdrant_client
        self._embeddings = embeddings
        self._llm = llm
        self._settings = settings

    def _truncate(self, text: str, limit: int = VK_MSG_LIMIT) -> str:
        """Truncate *text* to fit VK message length limit."""
        return _truncate(text, limit)

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

        from app.rag.chain import build_rag_chain
        from app.rag.prompts import DOCUMENT_EXPERTS_PROMPT
        from app.rag.retriever import build_retriever_for_document

        retriever = build_retriever_for_document(
            self._settings,
            document_id,
            qdrant_client=self._qdrant_client,
            embeddings=self._embeddings,
            collection_name=self._settings.qdrant_collection,
        )
        return build_rag_chain(retriever, self._llm, system_prompt=DOCUMENT_EXPERTS_PROMPT)

    async def ask(self, question: str) -> str:
        """Query the RAG chain and return a displayable answer string.

        * If the chain was not initialised → ``ERR_NO_ANSWER``.
        * If the chain raises at runtime → ``ERR_DOCUMENT_UNAVAILABLE``.
        * Long answers are truncated to fit the VK message limit.
        """
        if self._chain is None:
            return ERR_NO_ANSWER

        try:
            answer: str = await self._chain.ainvoke(question)
        except Exception:
            logger.error("RAG chain failed for question: %s", question, exc_info=True)
            return ERR_DOCUMENT_UNAVAILABLE

        if not answer or not answer.strip():
            return ERR_NO_ANSWER

        return self._truncate(answer.strip())

    async def ask_about_document(self, question: str, document_id: str) -> str:
        """Query the RAG chain scoped to a specific document and return a displayable answer string.

        * If the QA service was not initialised → ``ERR_NO_ANSWER``.
        * If the chain raises at runtime → ``ERR_DOCUMENT_UNAVAILABLE``.
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

        return self._truncate(answer.strip())

    async def stream_ask(self, question: str):
        """Stream tokens from the global RAG chain.

        Yields each token string as it arrives from the LLM.
        """
        if self._chain is None:
            yield ERR_NO_ANSWER
            return

        try:
            async for token in self._chain.astream(question):
                if isinstance(token, str):
                    yield token
                elif hasattr(token, "content"):
                    yield str(token.content)
                else:
                    yield str(token)
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

        * If the QA service was not initialised → yields error message.
        * If the chain raises at runtime → yields error message.
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
        except Exception:
            logger.error(
                "RAG chain streaming failed for document %s question: %s",
                document_id,
                question,
                exc_info=True,
            )
            yield ERR_DOCUMENT_UNAVAILABLE

    def close(self) -> None:
        """Release resources held by the QA service."""
        if self._qdrant_client is not None:
            try:
                self._qdrant_client.close()
            except Exception:
                logger.warning("Error closing Qdrant client", exc_info=True)

        self._chain = None
        self._qdrant_client = None
        self._settings = None
        self._embeddings = None
        self._llm = None
