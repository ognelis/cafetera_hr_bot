"""Asymmetric embedding wrapper: applies an instruction prefix to queries only.

Used for models like Qwen3-Embedding and E5-instruct which require
``Instruct: {task}\\nQuery: {text}`` formatting on the query side while
passages are embedded as-is.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings


class InstructedQueryEmbeddings(Embeddings):
    """Wrap an Embeddings instance, applying a Qwen3-style instruction
    prefix to query calls. Document calls are passed through unchanged.
    """

    def __init__(self, inner: Embeddings, instruction: str) -> None:
        self._inner = inner
        self._instruction = instruction.strip()

    def _format_query(self, text: str) -> str:
        return f"Instruct: {self._instruction}\nQuery: {text}"

    # Passages: no prefix
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._inner.aembed_documents(texts)

    # Queries: wrapped
    def embed_query(self, text: str) -> list[float]:
        return self._inner.embed_query(self._format_query(text))

    async def aembed_query(self, text: str) -> list[float]:
        return await self._inner.aembed_query(self._format_query(text))
