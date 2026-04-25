"""Tests for category-aware RAG prompts (CATEGORY_HINTS integration)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cafetera_core.rag.prompts import CATEGORY_HINTS
from cafetera_vk_bot.domain.topic_hints import _SCENARIO_KEYWORDS


class TestCategoryHintsKeysMatchKnownScenarios:
    """Verify CATEGORY_HINTS keys are a subset of known scenario IDs."""

    def test_all_category_hint_keys_exist_in_scenarios(self):
        """All CATEGORY_HINTS keys must exist in _SCENARIO_KEYWORDS."""
        category_keys = set(CATEGORY_HINTS.keys())
        scenario_keys = set(_SCENARIO_KEYWORDS.keys())

        assert category_keys.issubset(scenario_keys), (
            f"CATEGORY_HINTS has keys not in _SCENARIO_KEYWORDS: "
            f"{category_keys - scenario_keys}"
        )

    def test_category_hints_keys_are_expected(self):
        """CATEGORY_HINTS contains expected keys."""
        expected_keys = {"pay", "sick", "probation", "hire", "fire", "vacation"}
        assert set(CATEGORY_HINTS.keys()) == expected_keys


class TestBuildRagChainWithCategoryHint:
    """Test that build_rag_chain() with category_hint includes hint in prompt."""

    def test_build_rag_chain_with_category_hint_includes_hint_text(self):
        """Chain built with category_hint should include 'Дополнительный контекст' and hint."""
        from cafetera_core.rag.chain import build_rag_chain

        mock_retriever = MagicMock()
        mock_llm = MagicMock()
        hint_text = "Test category hint for pay questions"

        chain = build_rag_chain(
            retriever=mock_retriever,
            llm=mock_llm,
            system_prompt="Base system prompt",
            category_hint=hint_text,
        )

        # Access the prompt template through the chain structure
        # The chain is: {"context": ..., "question": ...} | prompt | llm | parser
        # We need to extract the prompt from the chain steps
        prompt_step = chain.steps[1]  # Second step is the prompt
        messages = prompt_step.messages

        # First message should be system message with hint
        system_message = messages[0]
        prompt_template = system_message.prompt.template

        assert "Дополнительный контекст" in prompt_template
        assert hint_text in prompt_template
        assert "Base system prompt" in prompt_template

    def test_build_rag_chain_with_actual_category_hint_from_dict(self):
        """Chain built with actual CATEGORY_HINTS value includes the hint."""
        from cafetera_core.rag.chain import build_rag_chain

        mock_retriever = MagicMock()
        mock_llm = MagicMock()
        hint_text = CATEGORY_HINTS["pay"]

        chain = build_rag_chain(
            retriever=mock_retriever,
            llm=mock_llm,
            system_prompt="Base prompt",
            category_hint=hint_text,
        )

        prompt_step = chain.steps[1]
        messages = prompt_step.messages
        system_message = messages[0]
        prompt_template = system_message.prompt.template

        assert "Дополнительный контекст" in prompt_template
        assert "оплате труда" in prompt_template  # Part of pay hint


class TestBuildRagChainWithoutCategoryHint:
    """Test that build_rag_chain() without category_hint does NOT include hint marker."""

    def test_build_rag_chain_without_hint_excludes_context_marker(self):
        """Chain built without category_hint should not include 'Дополнительный контекст'."""
        from cafetera_core.rag.chain import build_rag_chain

        mock_retriever = MagicMock()
        mock_llm = MagicMock()

        chain = build_rag_chain(
            retriever=mock_retriever,
            llm=mock_llm,
            system_prompt="Base system prompt",
            category_hint=None,
        )

        prompt_step = chain.steps[1]
        messages = prompt_step.messages
        system_message = messages[0]
        prompt_template = system_message.prompt.template

        assert "Дополнительный контекст" not in prompt_template
        assert prompt_template == "Base system prompt"

    def test_build_rag_chain_with_empty_string_hint(self):
        """Chain built with empty string hint should not add context section."""
        from cafetera_core.rag.chain import build_rag_chain

        mock_retriever = MagicMock()
        mock_llm = MagicMock()

        chain = build_rag_chain(
            retriever=mock_retriever,
            llm=mock_llm,
            system_prompt="Base system prompt",
            category_hint="",
        )

        prompt_step = chain.steps[1]
        messages = prompt_step.messages
        system_message = messages[0]
        prompt_template = system_message.prompt.template

        # Empty string is falsy, so no context should be added
        assert "Дополнительный контекст" not in prompt_template


class TestQAServiceAskPassesCategory:
    """Test that QAService.ask() correctly passes category through to chain building."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for QAService tests."""
        settings = MagicMock()
        settings.qdrant_collection = "test_collection"
        return settings

    @pytest.fixture
    def qa_service_with_mocks(self, mock_settings):
        """Create a QAService with all required mocks."""
        service = MagicMock()
        from cafetera_core.domain.qa_service import QAService

        service = QAService(
            qdrant_client=MagicMock(),
            embeddings=MagicMock(),
            llm=MagicMock(),
            settings=mock_settings,
            global_system_prompt="Test system prompt",
        )
        return service

    async def test_ask_passes_category_to_build_global_chain(self, qa_service_with_mocks):
        """ask() should pass category parameter to _build_global_chain."""
        service = qa_service_with_mocks

        with patch.object(service, "_build_global_chain") as mock_build:
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value="Test answer")
            mock_build.return_value = mock_chain

            await service.ask("Какая зарплата?", category="pay")

            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args
            # category should be passed as keyword argument
            assert call_kwargs.kwargs.get("category") == "pay"

    async def test_ask_with_none_category(self, qa_service_with_mocks):
        """ask() without category should pass None to _build_global_chain."""
        service = qa_service_with_mocks

        with patch.object(service, "_build_global_chain") as mock_build:
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value="Test answer")
            mock_build.return_value = mock_chain

            await service.ask("Какая зарплата?")

            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args
            assert call_kwargs.kwargs.get("category") is None

    async def test_stream_ask_passes_category(self, qa_service_with_mocks):
        """stream_ask() should pass category parameter to _build_global_chain."""
        service = qa_service_with_mocks

        with patch.object(service, "_build_global_chain") as mock_build:
            mock_chain = MagicMock()
            mock_chain.astream = MagicMock(return_value=async_iter(["Test", " answer"]))
            mock_build.return_value = mock_chain

            async for _ in service.stream_ask("Какая зарплата?", category="pay"):
                pass

            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args
            assert call_kwargs.kwargs.get("category") == "pay"

    def test_build_global_chain_uses_category_hint(self, qa_service_with_mocks):
        """_build_global_chain should look up hint from CATEGORY_HINTS using category."""
        service = qa_service_with_mocks

        with patch("cafetera_core.rag.chain.build_rag_chain") as mock_build_chain:
            with patch("cafetera_core.rag.retriever.build_retriever") as mock_build_retriever:
                mock_retriever = MagicMock()
                mock_build_retriever.return_value = mock_retriever

                # Call with category="pay"
                service._build_global_chain(k=4, category="pay")

                # Verify build_rag_chain was called with correct category_hint
                mock_build_chain.assert_called_once()
                call_kwargs = mock_build_chain.call_args.kwargs
                assert call_kwargs.get("category_hint") == CATEGORY_HINTS["pay"]

    def test_build_global_chain_with_unknown_category(self, qa_service_with_mocks):
        """_build_global_chain should handle unknown category gracefully."""
        service = qa_service_with_mocks

        with patch("cafetera_core.rag.chain.build_rag_chain") as mock_build_chain:
            with patch("cafetera_core.rag.retriever.build_retriever") as mock_build_retriever:
                mock_retriever = MagicMock()
                mock_build_retriever.return_value = mock_retriever

                # Call with unknown category
                service._build_global_chain(k=4, category="unknown_category")

                mock_build_chain.assert_called_once()
                call_kwargs = mock_build_chain.call_args.kwargs
                # Unknown category should result in None hint
                assert call_kwargs.get("category_hint") is None


# Helper for async iteration
async def async_iter(items):
    """Helper to create async iterator from list."""
    for item in items:
        yield item
