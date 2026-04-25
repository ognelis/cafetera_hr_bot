"""RAG chain: retriever -> prompt -> LLM -> answer."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.runnables import Runnable

    from cafetera_core.config import CoreSettings

logger = logging.getLogger(__name__)


def _format_docs(docs: list[Document]) -> str:
    """Join retrieved document page contents into a single context string."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def _format_docs_with_metadata(docs: list[Document]) -> str:
    """Join retrieved documents with filename metadata headers.

    Format:
        [Документ: filename.docx]
        chunk text here

        ---

        [Документ: another.docx]
        another chunk text

    If filename is missing/empty, outputs plain text without header.
    """
    formatted_chunks: list[str] = []
    for doc in docs:
        filename = doc.metadata.get("filename", "")
        if filename:
            formatted_chunks.append(f"[Документ: {filename}]\n{doc.page_content}")
        else:
            formatted_chunks.append(doc.page_content)
    return "\n\n---\n\n".join(formatted_chunks)


def build_llm(settings: CoreSettings) -> BaseChatModel:
    """Create a chat LLM instance based on ``settings.llm_provider``."""
    if settings.llm_provider == "openai":
        try:
            from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            temperature=0.3,
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
            temperature=0.3,
        )

    # Default: Ollama
    try:
        from langchain_ollama import ChatOllama  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "Install the 'ollama' extra: uv sync --extra ollama"
        ) from exc
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        temperature=0.3,
    )


def build_rag_chain(
    retriever: BaseRetriever,
    llm: BaseChatModel,
    *,
    system_prompt: str | None,
    include_metadata: bool = False,
    category_hint: str | None = None,
) -> Runnable:
    """Build a RAG chain: retrieve -> format context -> prompt -> LLM -> text."""
    prompt_template = system_prompt or ""
    if category_hint:
        prompt_template = f"{prompt_template}\n\nДополнительный контекст:\n{category_hint}"
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_template),
        ("human", "{question}"),
    ])

    formatter = _format_docs_with_metadata if include_metadata else _format_docs
    chain: Runnable = (
        {"context": retriever | formatter, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    logger.info("RAG chain built successfully")
    return chain
