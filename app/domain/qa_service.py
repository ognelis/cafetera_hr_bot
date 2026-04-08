"""Domain QA service — wraps the RAG chain for use by transport handlers.

Initialised once at startup via ``init_qa(settings)``.  Handlers call
``await ask(question)`` which always returns a displayable string, even
on error.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.domain.content import ERR_DOCUMENT_UNAVAILABLE, ERR_NO_ANSWER

# Settings reference for document-scoped queries
_settings: Settings | None = None

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable
    from qdrant_client import QdrantClient

    from app.config import Settings

logger = logging.getLogger(__name__)

# ── module-level state (set once by init_qa) ──────────────────────

_chain: Runnable | None = None
_qdrant_client: QdrantClient | None = None

VK_MSG_LIMIT = 4096
_TRUNCATION_SUFFIX = "\n\n…Обратитесь в HR-отдел для полной информации."
_CUT_AT = VK_MSG_LIMIT - len(_TRUNCATION_SUFFIX)


# ── private helpers ───────────────────────────────────────────────


def _truncate(text: str, limit: int = VK_MSG_LIMIT) -> str:
    """Truncate *text* to fit VK message length limit."""
    if len(text) <= limit:
        return text
    cut = text[: _CUT_AT]
    # cut at last space to avoid splitting a word
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut + _TRUNCATION_SUFFIX


# ── public API ────────────────────────────────────────────────────


def init_qa(settings: Settings) -> None:
    """Build the RAG chain and store it for later use by ``ask()``.

    Safe to call even when Qdrant or the LLM provider is unavailable —
    logs a warning and leaves the chain as *None* so the bot can still
    start (handlers will return a user-friendly fallback).
    """
    global _chain, _qdrant_client, _settings  # noqa: PLW0603

    if _qdrant_client is not None:
        _qdrant_client.close()
        _qdrant_client = None
        _chain = None

    try:
        from qdrant_client import QdrantClient as _QC

        from app.rag.chain import build_llm, build_rag_chain
        from app.rag.retriever import build_embeddings, build_retriever

        client = _QC(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        embeddings = build_embeddings(settings)
        retriever = build_retriever(
            client,
            embeddings,
            settings.qdrant_collection,
        )
        llm = build_llm(settings)
        chain = build_rag_chain(retriever, llm)

        _qdrant_client = client
        _chain = chain
        _settings = settings
        logger.info("RAG chain initialised successfully")
    except Exception:
        logger.warning("RAG chain not available — handlers will use fallback", exc_info=True)


async def ask(question: str) -> str:
    """Query the RAG chain and return a displayable answer string.

    * If the chain was not initialised → ``ERR_NO_ANSWER``.
    * If the chain raises at runtime → ``ERR_DOCUMENT_UNAVAILABLE``.
    * Long answers are truncated to fit the VK message limit.
    """
    if _chain is None:
        return ERR_NO_ANSWER

    try:
        answer: str = await _chain.ainvoke(question)
    except Exception:
        logger.error("RAG chain failed for question: %s", question, exc_info=True)
        return ERR_DOCUMENT_UNAVAILABLE

    if not answer or not answer.strip():
        return ERR_NO_ANSWER

    return _truncate(answer.strip())


async def ask_about_document(question: str, document_id: str) -> str:
    """Query the RAG chain scoped to a specific document and return a displayable answer string.

    * If the QA service was not initialised → ``ERR_NO_ANSWER``.
    * If the chain raises at runtime → ``ERR_DOCUMENT_UNAVAILABLE``.
    * Long answers are truncated to fit the VK message limit.
    """
    if _qdrant_client is None or _settings is None:
        return ERR_NO_ANSWER

    try:
        from app.rag.chain import build_llm, build_rag_chain
        from app.rag.prompts import DOCUMENT_EXPERTS_PROMPT
        from app.rag.retriever import build_embeddings, build_retriever_for_document

        embeddings = build_embeddings(_settings)
        retriever = build_retriever_for_document(
            _qdrant_client,
            embeddings,
            document_id,
            _settings.qdrant_collection,
        )
        llm = build_llm(_settings)
        chain = build_rag_chain(retriever, llm, system_prompt=DOCUMENT_EXPERTS_PROMPT)
        answer: str = await chain.ainvoke(question)
    except Exception:
        logger.error(
            "RAG chain failed for document %s question: %s", document_id, question, exc_info=True
        )
        return ERR_DOCUMENT_UNAVAILABLE

    if not answer or not answer.strip():
        return ERR_NO_ANSWER

    return _truncate(answer.strip())


def close_qa() -> None:
    """Release resources held by the QA service."""
    global _chain, _qdrant_client, _settings  # noqa: PLW0603

    if _qdrant_client is not None:
        try:
            _qdrant_client.close()
        except Exception:
            logger.warning("Error closing Qdrant client", exc_info=True)

    _chain = None
    _qdrant_client = None
    _settings = None
