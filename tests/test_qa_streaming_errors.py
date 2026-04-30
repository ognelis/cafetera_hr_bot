"""Tests for QAService streaming cancellation and error handling."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from cafetera_rag_service.qa_service import (
    ERR_DOCUMENT_UNAVAILABLE,
    ERR_NO_ANSWER,
    QAService,
)


def _make_qa_service(mock_chain):
    """Create a QAService with mocked internals that returns mock_chain."""
    svc = QAService()
    svc._build_global_chain = MagicMock(return_value=mock_chain)
    svc._build_document_chain = MagicMock(return_value=mock_chain)
    svc._settings = MagicMock(global_max_k=10)
    return svc


# ---------------------------------------------------------------------------
# 1. CancelledError re-raises
# ---------------------------------------------------------------------------


@patch("cafetera_rag_service.rag.retriever.estimate_k", return_value=4)
async def test_stream_ask_reraises_cancelled_error(mock_k):
    """stream_ask must re-raise CancelledError for proper cleanup."""

    async def _exploding_stream(*a, **kw):
        raise asyncio.CancelledError()
        yield  # make it a generator  # noqa: RUF

    mock_chain = MagicMock()
    mock_chain.astream = _exploding_stream
    svc = _make_qa_service(mock_chain)

    with pytest.raises(asyncio.CancelledError):
        async for _ in svc.stream_ask("test"):
            pass


async def test_stream_about_document_reraises_cancelled_error():
    """stream_about_document must re-raise CancelledError."""

    async def _exploding_stream(*a, **kw):
        raise asyncio.CancelledError()
        yield  # noqa: RUF

    mock_chain = MagicMock()
    mock_chain.astream = _exploding_stream
    svc = _make_qa_service(mock_chain)

    with pytest.raises(asyncio.CancelledError):
        async for _ in svc.stream_about_document("test", "doc-1"):
            pass


# ---------------------------------------------------------------------------
# 2. Generic Exception yields error message
# ---------------------------------------------------------------------------


@patch("cafetera_rag_service.rag.retriever.estimate_k", return_value=4)
async def test_stream_ask_yields_error_on_exception(mock_k):
    """stream_ask yields ERR_DOCUMENT_UNAVAILABLE on generic exception."""

    async def _failing_stream(*a, **kw):
        raise RuntimeError("LLM exploded")
        yield  # noqa: RUF

    mock_chain = MagicMock()
    mock_chain.astream = _failing_stream
    svc = _make_qa_service(mock_chain)

    tokens = [t async for t in svc.stream_ask("test")]
    assert tokens == [ERR_DOCUMENT_UNAVAILABLE]


async def test_stream_about_document_yields_error_on_exception():
    """stream_about_document yields ERR_DOCUMENT_UNAVAILABLE on generic exception."""

    async def _failing_stream(*a, **kw):
        raise RuntimeError("LLM exploded")
        yield  # noqa: RUF

    mock_chain = MagicMock()
    mock_chain.astream = _failing_stream
    svc = _make_qa_service(mock_chain)

    tokens = [t async for t in svc.stream_about_document("test", "doc-1")]
    assert tokens == [ERR_DOCUMENT_UNAVAILABLE]


# ---------------------------------------------------------------------------
# 3. Successful token yield
# ---------------------------------------------------------------------------


@patch("cafetera_rag_service.rag.retriever.estimate_k", return_value=4)
async def test_stream_ask_yields_tokens(mock_k):
    """stream_ask yields tokens from the chain."""

    async def _token_stream(*a, **kw):
        yield "Hello"
        yield " world"

    mock_chain = MagicMock()
    mock_chain.astream = _token_stream
    svc = _make_qa_service(mock_chain)

    tokens = [t async for t in svc.stream_ask("test")]
    assert tokens == ["Hello", " world"]


# ---------------------------------------------------------------------------
# 4. None chain yields ERR_NO_ANSWER
# ---------------------------------------------------------------------------


@patch("cafetera_rag_service.rag.retriever.estimate_k", return_value=4)
async def test_stream_ask_no_chain_yields_no_answer(mock_k):
    """stream_ask yields ERR_NO_ANSWER when chain is not initialized."""
    svc = QAService()
    svc._settings = MagicMock(global_max_k=10)

    tokens = [t async for t in svc.stream_ask("test")]
    assert tokens == [ERR_NO_ANSWER]


async def test_stream_about_document_no_chain_yields_no_answer():
    """stream_about_document yields ERR_NO_ANSWER when chain is not built."""
    svc = QAService()

    tokens = [t async for t in svc.stream_about_document("test", "doc-1")]
    assert tokens == [ERR_NO_ANSWER]
