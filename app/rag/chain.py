"""RAG chain: retriever -> prompt -> LLM -> answer."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from app.rag.prompts import SYSTEM_PROMPT

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import Runnable
    from langchain_core.vectorstores import VectorStoreRetriever

    from app.config import Settings

logger = logging.getLogger(__name__)


def _format_docs(docs: list[Document]) -> str:
    """Join retrieved document page contents into a single context string."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def build_llm(settings: Settings) -> BaseChatModel:
    """Create a chat LLM instance based on ``settings.llm_provider``."""
    if settings.llm_provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            temperature=0.1,
        )

    if settings.llm_provider == "llamacpp":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key or "no-key",
            base_url=settings.llm_base_url or "http://localhost:8080/v1",
            temperature=0.1,
        )

    # Default: Ollama
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise ImportError(
            "Install the 'ollama' extra: uv sync --extra ollama"
        ) from exc
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        temperature=0.1,
    )


def build_rag_chain(
    retriever: VectorStoreRetriever,
    llm: BaseChatModel,
) -> Runnable:
    """Build a RAG chain: retrieve -> format context -> prompt -> LLM -> text."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    logger.info("RAG chain built successfully")
    return chain
