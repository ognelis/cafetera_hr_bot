"""Tests for Block 7 — QA service (RAG chain wrapper)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain import qa_service
from app.domain.content import ERR_DOCUMENT_UNAVAILABLE, ERR_NO_ANSWER

# ── helpers ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_qa_state():
    """Ensure module-level state is clean before and after each test."""
    qa_service._chain = None
    qa_service._qdrant_client = None
    yield
    qa_service._chain = None
    qa_service._qdrant_client = None


# ── ask() ──────────────────────────────────────────────────────────


class TestAsk:
    async def test_returns_fallback_when_chain_is_none(self):
        result = await qa_service.ask("Любой вопрос")
        assert result == ERR_NO_ANSWER

    async def test_returns_answer_from_chain(self):
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = "Ответ из базы знаний."
        qa_service._chain = mock_chain

        result = await qa_service.ask("Условия премирования")

        assert result == "Ответ из базы знаний."
        mock_chain.ainvoke.assert_awaited_once_with("Условия премирования")

    async def test_catches_chain_exception(self):
        mock_chain = AsyncMock()
        mock_chain.ainvoke.side_effect = RuntimeError("LLM timeout")
        qa_service._chain = mock_chain

        result = await qa_service.ask("Вопрос")

        assert result == ERR_DOCUMENT_UNAVAILABLE

    async def test_returns_fallback_for_empty_answer(self):
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = "   "
        qa_service._chain = mock_chain

        result = await qa_service.ask("Вопрос")

        assert result == ERR_NO_ANSWER

    async def test_truncates_long_response(self):
        long_text = "Слово " * 1500  # ~9000 chars
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = long_text
        qa_service._chain = mock_chain

        result = await qa_service.ask("Вопрос")

        assert len(result) <= qa_service.VK_MSG_LIMIT
        assert result.endswith("…Обратитесь в HR-отдел для полной информации.")


# ── _truncate() ────────────────────────────────────────────────────


class TestTruncate:
    def test_preserves_short_text(self):
        text = "Короткий ответ."
        assert qa_service._truncate(text) == text

    def test_truncates_at_limit(self):
        text = "a " * 3000  # 6000 chars
        result = qa_service._truncate(text)
        assert len(result) <= qa_service.VK_MSG_LIMIT

    def test_cuts_at_word_boundary(self):
        # Build text that is slightly over limit
        text = "word " * 1000  # 5000 chars
        result = qa_service._truncate(text)
        # The truncated part (before suffix) should not end mid-word
        before_suffix = result.removesuffix(qa_service._TRUNCATION_SUFFIX)
        assert not before_suffix.endswith("wor")  # no partial word

    def test_exact_limit_not_truncated(self):
        text = "a" * qa_service.VK_MSG_LIMIT
        assert qa_service._truncate(text) == text


# ── init_qa() ──────────────────────────────────────────────────────


class TestInitQa:
    @patch("app.rag.chain.build_rag_chain")
    @patch("app.rag.chain.build_llm")
    @patch("app.rag.retriever.build_retriever")
    @patch("app.rag.retriever.build_embeddings")
    @patch("qdrant_client.QdrantClient")
    def test_success_with_mocks(
        self,
        mock_qc,
        mock_embeddings,
        mock_retriever,
        mock_llm,
        mock_chain,
    ):
        mock_chain.return_value = MagicMock()
        mock_settings = MagicMock()
        mock_settings.qdrant_url = "http://localhost:6333"
        mock_settings.qdrant_api_key = None
        mock_settings.qdrant_collection = "hr_documents"

        qa_service.init_qa(mock_settings)

        assert qa_service._chain is not None
        assert qa_service._qdrant_client is not None

    @patch(
        "qdrant_client.QdrantClient",
        side_effect=RuntimeError("Connection refused"),
    )
    def test_survives_qdrant_failure(self, _mock_qc):
        mock_settings = MagicMock()
        mock_settings.qdrant_url = "http://localhost:6333"
        mock_settings.qdrant_api_key = None
        mock_settings.qdrant_collection = "hr_documents"

        qa_service.init_qa(mock_settings)

        assert qa_service._chain is None


# ── close_qa() ─────────────────────────────────────────────────────


class TestCloseQa:
    def test_resets_state(self):
        qa_service._chain = MagicMock()
        qa_service._qdrant_client = MagicMock()

        qa_service.close_qa()

        assert qa_service._chain is None
        assert qa_service._qdrant_client is None

    def test_closes_qdrant_client(self):
        mock_client = MagicMock()
        qa_service._qdrant_client = mock_client

        qa_service.close_qa()

        mock_client.close.assert_called_once()

    def test_survives_close_error(self):
        mock_client = MagicMock()
        mock_client.close.side_effect = RuntimeError("close failed")
        qa_service._qdrant_client = mock_client

        qa_service.close_qa()  # should not raise

        assert qa_service._qdrant_client is None


# ── handler imports ────────────────────────────────────────────────


class TestHandlerImports:
    """Verify that P0 handlers now import qa_service (Block 7)."""

    def test_fire_handler_imports_qa_service(self):
        from app.integrations.vk.handlers import fire

        assert hasattr(fire, "qa_service")

    def test_vacation_handler_imports_qa_service(self):
        from app.integrations.vk.handlers import vacation

        assert hasattr(vacation, "qa_service")

    def test_pay_handler_imports_qa_service(self):
        from app.integrations.vk.handlers import pay

        assert hasattr(pay, "qa_service")
