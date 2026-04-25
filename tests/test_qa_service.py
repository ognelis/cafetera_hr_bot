"""Tests for Block 7 — QA service (RAG chain wrapper)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cafetera_core.domain.content import ERR_DOCUMENT_UNAVAILABLE, ERR_NO_ANSWER
from cafetera_core.domain.qa_service import (
    _TRUNCATION_SUFFIX,
    VK_MSG_LIMIT,
    QAService,
    _truncate,
)

# ── fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_settings():
    """Create mock settings for QAService tests."""
    settings = MagicMock()
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_api_key = None
    settings.qdrant_collection = "hr_documents"
    return settings


@pytest.fixture
def qa_service_with_mock_chain(mock_settings):
    """Create a QAService instance with a mock chain."""
    mock_chain = AsyncMock()
    service = QAService(
        chain=mock_chain,
        qdrant_client=MagicMock(),
        embeddings=MagicMock(),
        llm=MagicMock(),
        settings=mock_settings,
    )
    # Mock _build_global_chain to return the mock chain for ask/stream_ask tests
    service._build_global_chain = MagicMock(return_value=mock_chain)
    return service, mock_chain


# ── ask() ──────────────────────────────────────────────────────────


class TestAsk:
    async def test_returns_fallback_when_chain_is_none(self):
        service = QAService()
        result = await service.ask("Любой вопрос")
        assert result == ERR_NO_ANSWER

    async def test_returns_answer_from_chain(self, qa_service_with_mock_chain):
        service, mock_chain = qa_service_with_mock_chain
        mock_chain.ainvoke.return_value = "Ответ из базы знаний."

        result = await service.ask("Условия премирования")

        assert result == "Ответ из базы знаний."
        mock_chain.ainvoke.assert_awaited_once_with("Условия премирования")

    async def test_catches_chain_exception(self, qa_service_with_mock_chain):
        service, mock_chain = qa_service_with_mock_chain
        mock_chain.ainvoke.side_effect = RuntimeError("LLM timeout")

        result = await service.ask("Вопрос")

        assert result == ERR_DOCUMENT_UNAVAILABLE

    async def test_returns_fallback_for_empty_answer(self, qa_service_with_mock_chain):
        service, mock_chain = qa_service_with_mock_chain
        mock_chain.ainvoke.return_value = "   "

        result = await service.ask("Вопрос")

        assert result == ERR_NO_ANSWER

    async def test_truncates_long_response(self, qa_service_with_mock_chain):
        service, mock_chain = qa_service_with_mock_chain
        long_text = "Слово " * 1500  # ~9000 chars
        mock_chain.ainvoke.return_value = long_text

        result = await service.ask("Вопрос")

        assert len(result) <= VK_MSG_LIMIT
        assert result.endswith("…Обратитесь в HR-отдел для полной информации.")


# ── _truncate() ────────────────────────────────────────────────────


class TestTruncate:
    def test_preserves_short_text(self):
        text = "Короткий ответ."
        assert _truncate(text) == text

    def test_truncates_at_limit(self):
        text = "a " * 3000  # 6000 chars
        result = _truncate(text)
        assert len(result) <= VK_MSG_LIMIT

    def test_cuts_at_word_boundary(self):
        # Build text that is slightly over limit
        text = "word " * 1000  # 5000 chars
        result = _truncate(text)
        # The truncated part (before suffix) should not end mid-word
        before_suffix = result.removesuffix(_TRUNCATION_SUFFIX)
        assert not before_suffix.endswith("wor")  # no partial word

    def test_exact_limit_not_truncated(self):
        text = "a" * VK_MSG_LIMIT
        assert _truncate(text) == text


# ── QAService.__init__() ───────────────────────────────────────────


class TestQAServiceInit:
    def test_initializes_with_all_dependencies(self, mock_settings):
        mock_chain = MagicMock()
        mock_qdrant = MagicMock()
        mock_embeddings = MagicMock()
        mock_llm = MagicMock()

        service = QAService(
            chain=mock_chain,
            qdrant_client=mock_qdrant,
            embeddings=mock_embeddings,
            llm=mock_llm,
            settings=mock_settings,
        )

        assert service._chain is mock_chain
        assert service._qdrant_client is mock_qdrant
        assert service._embeddings is mock_embeddings
        assert service._llm is mock_llm
        assert service._settings is mock_settings

    def test_initializes_with_none_defaults(self):
        service = QAService()

        assert service._chain is None
        assert service._qdrant_client is None
        assert service._embeddings is None
        assert service._llm is None
        assert service._settings is None

    def test_initializes_with_partial_dependencies(self, mock_settings):
        mock_chain = MagicMock()

        service = QAService(
            chain=mock_chain,
            settings=mock_settings,
        )

        assert service._chain is mock_chain
        assert service._qdrant_client is None
        assert service._embeddings is None
        assert service._llm is None
        assert service._settings is mock_settings


# ── QAService.close() ──────────────────────────────────────────────


class TestQAServiceClose:
    def test_resets_state(self, mock_settings):
        mock_chain = MagicMock()
        mock_qdrant = MagicMock()
        mock_embeddings = MagicMock()
        mock_llm = MagicMock()

        service = QAService(
            chain=mock_chain,
            qdrant_client=mock_qdrant,
            embeddings=mock_embeddings,
            llm=mock_llm,
            settings=mock_settings,
        )

        service.close()

        assert service._chain is None
        assert service._qdrant_client is None
        assert service._embeddings is None
        assert service._llm is None
        assert service._settings is None

    def test_does_not_close_qdrant_client(self, mock_settings):
        """QAService should not close Qdrant client - lifecycle is managed externally."""
        mock_client = MagicMock()
        service = QAService(
            qdrant_client=mock_client,
            settings=mock_settings,
        )

        service.close()

        # Qdrant client lifecycle is managed by the creator (e.g., lifespan)
        mock_client.close.assert_not_called()
        assert service._qdrant_client is None

    def test_close_with_none_qdrant_client(self):
        service = QAService()

        service.close()  # should not raise

        assert service._qdrant_client is None


# ── handler imports ────────────────────────────────────────────────


class TestHandlerImports:
    """Verify that P0+P1 handlers use send_rag_answer helper (Block 7+8)."""

    def test_fire_handler_imports_send_rag_answer(self):
        from cafetera_vk_bot.handlers import fire

        assert hasattr(fire, "send_rag_answer")

    def test_vacation_handler_imports_send_rag_answer(self):
        from cafetera_vk_bot.handlers import vacation

        assert hasattr(vacation, "send_rag_answer")

    def test_pay_handler_imports_send_rag_answer(self):
        from cafetera_vk_bot.handlers import pay

        assert hasattr(pay, "send_rag_answer")

    def test_sections_handler_imports_send_rag_answer(self):
        from cafetera_vk_bot.handlers import sections

        assert hasattr(sections, "send_rag_answer")
