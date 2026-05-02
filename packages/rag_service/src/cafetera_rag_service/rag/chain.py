"""RAG chain: retriever -> prompt -> LLM -> answer."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.runnables import Runnable

    from cafetera_rag_service.config import RagServiceSettings
    from cafetera_rag_service.rag.reranker import HttpRerankerClient

logger = logging.getLogger(__name__)


def _format_docs(docs: list[Document]) -> str:
    """Join retrieved document page contents into a single context string."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def _format_docs_with_metadata(docs: list[Document]) -> str:
    """Join retrieved documents with metadata headers.

    Format:
        [Документ: filename.docx | стр. 5, 6]
        chunk text here

        ---

        [Документ: another.docx]
        another chunk text

    Includes filename and page numbers when available.
    Section headings are omitted from the header because
    ``page_content`` already contains them — the parser prepends
    the heading hierarchy from chunk metadata.
    If no metadata is present, outputs plain text.
    """
    formatted_chunks: list[str] = []
    for doc in docs:
        filename = doc.metadata.get("filename", "")
        page_numbers = doc.metadata.get("page_numbers", [])

        header_parts: list[str] = []
        if filename:
            header_parts.append(f"Документ: {filename}")
        if page_numbers:
            header_parts.append(f"стр. {', '.join(str(p) for p in page_numbers)}")

        header = f"[{' | '.join(header_parts)}]\n" if header_parts else ""
        formatted_chunks.append(f"{header}{doc.page_content}")
    return "\n\n---\n\n".join(formatted_chunks)


def _openai_sampling_kwargs(settings: RagServiceSettings) -> dict[str, Any]:
    """Collect optional OpenAI-compatible sampling kwargs.

    ``top_p`` and ``presence_penalty`` are native Chat Completions parameters.
    ``top_k`` is non-standard for OpenAI but accepted by vLLM and llama-server
    via ``extra_body`` (passed directly to ``ChatOpenAI``).
    """
    extra: dict[str, Any] = {}
    if settings.llm_top_p is not None:
        extra["top_p"] = settings.llm_top_p
    if settings.llm_presence_penalty is not None:
        extra["presence_penalty"] = settings.llm_presence_penalty
    if settings.llm_top_k is not None:
        extra.setdefault("extra_body", {})["top_k"] = settings.llm_top_k
    return extra


def _ollama_sampling_kwargs(settings: RagServiceSettings) -> dict[str, Any]:
    """Collect optional Ollama sampling kwargs.

    Ollama natively supports ``top_p`` and ``top_k``. ``presence_penalty`` is
    not an Ollama option (it uses ``repeat_penalty`` instead) and is skipped.
    """
    extra: dict[str, Any] = {}
    if settings.llm_top_p is not None:
        extra["top_p"] = settings.llm_top_p
    if settings.llm_top_k is not None:
        extra["top_k"] = settings.llm_top_k
    if settings.llm_presence_penalty is not None:
        logger.info(
            "LLM_PRESENCE_PENALTY is ignored for the Ollama backend "
            "(Ollama uses repeat_penalty instead)."
        )
    return extra


def build_llm(settings: RagServiceSettings) -> BaseChatModel:
    """Create a chat LLM instance based on ``settings.llm_provider``."""
    if settings.llm_provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        logger.info(
            "LLM_NUM_CTX=%d (informational for openai provider "
            "— context window is model-defined)",
            settings.llm_num_ctx,
        )
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,  # type: ignore[arg-type]
            base_url=settings.llm_base_url or None,
            temperature=settings.llm_temperature,
            **_openai_sampling_kwargs(settings),
        )

    if settings.llm_provider == "llamacpp":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai_compatible' extra: "
                "uv sync --extra openai_compatible"
            ) from exc
        kwargs = _openai_sampling_kwargs(settings)
        extra_body = kwargs.setdefault("extra_body", {})
        extra_body["n_ctx"] = settings.llm_num_ctx
        if settings.llm_disable_thinking:
            extra_body["chat_template_kwargs"] = {"enable_thinking": False}
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key or "no-key",  # type: ignore[arg-type]
            base_url=settings.llm_base_url or "http://localhost:8080/v1",
            temperature=settings.llm_temperature,
            **kwargs,
        )

    # Default: Ollama
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise ImportError(
            "Install the 'ollama' extra: uv sync --extra ollama"
        ) from exc
    kwargs = _ollama_sampling_kwargs(settings)
    if settings.llm_disable_thinking:
        kwargs["model_kwargs"] = {"think": False}
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        num_ctx=settings.llm_num_ctx,
        **kwargs,
    )


def build_rag_chain(
    retriever: BaseRetriever,
    llm: BaseChatModel,
    *,
    system_prompt: str | None,
    include_metadata: bool = False,
    category_hint: str | None = None,
    reranker: HttpRerankerClient | None = None,
) -> Runnable:
    """Build a RAG chain: retrieve -> format context -> prompt -> LLM -> text."""
    prompt_template = system_prompt or ""
    if category_hint:
        prompt_template = (
            f"{prompt_template}\n\n"
            f"Дополнительный контекст:\n{category_hint}"
        )
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_template),
        ("human", "{question}"),
    ])

    if reranker is not None:
        from cafetera_rag_service.rag.reranker import RerankingRetriever

        retriever = RerankingRetriever(
            base_retriever=retriever,
            reranker=reranker,
        )

    formatter = (
        _format_docs_with_metadata if include_metadata else _format_docs
    )
    chain: Runnable = (
        {
            "context": retriever | formatter,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    logger.info("RAG chain built successfully")
    return chain
