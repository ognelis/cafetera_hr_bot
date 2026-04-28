"""QA endpoints — ask questions and stream answers."""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from cafetera_rag_service.api.deps import verify_api_key
from cafetera_rag_service.models import (
    AskDocumentRequest,
    AskRequest,
    AskResponse,
)
from cafetera_rag_service.qa_service import QAService
from cafetera_rag_service.resources import build_qa_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/qa", tags=["qa"], dependencies=[Depends(verify_api_key)])


def _get_or_create_qa_service(
    request: Request, system_prompt: str, include_metadata: bool
) -> QAService:
    """Return a cached QAService for the given (prompt, metadata) pair.

    Uses an LRU dict on ``app.state.qa_services`` keyed by
    ``(prompt_hash, include_metadata)``.
    """
    prompt_hash = hashlib.sha256(system_prompt.encode()).hexdigest()[:16]
    cache_key = (prompt_hash, include_metadata)

    qa_cache: dict = request.app.state.qa_services
    if cache_key in qa_cache:
        return qa_cache[cache_key]

    rag_resources = request.app.state.rag_resources
    try:
        qa = build_qa_service(rag_resources, system_prompt, include_metadata=include_metadata)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Simple bounded cache — evict oldest when over 32 entries
    if len(qa_cache) >= 32:
        oldest_key = next(iter(qa_cache))
        qa_cache.pop(oldest_key)
    qa_cache[cache_key] = qa
    return qa


@router.post("/ask", response_model=AskResponse)
async def ask(request: Request, body: AskRequest) -> AskResponse:
    """Ask a question via the RAG chain and return the answer."""
    qa = _get_or_create_qa_service(request, body.system_prompt, body.include_metadata)
    answer = await qa.ask(body.question, category=body.category)
    return AskResponse(answer=answer)


@router.post("/stream")
async def stream_ask(request: Request, body: AskRequest):
    """Stream tokens from the RAG chain as SSE events."""
    qa = _get_or_create_qa_service(request, body.system_prompt, body.include_metadata)

    async def event_generator():
        try:
            async for token in qa.stream_ask(body.question, category=body.category):
                escaped = (
                    token.replace("\\", "\\\\")
                    .replace('"', '\\"')
                    .replace("\n", "\\n")
                )
                yield f'data: {{"token": "{escaped}"}}\n\n'
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("SSE stream error: %s", exc, exc_info=True)
            yield 'data: {"error": "Internal error"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/ask-document", response_model=AskResponse)
async def ask_document(request: Request, body: AskDocumentRequest) -> AskResponse:
    """Ask a question about a specific document."""
    # Use a default system prompt for document-scoped questions
    qa = _get_or_create_qa_service(request, "", include_metadata=False)
    answer = await qa.ask_about_document(body.question, body.document_id)
    return AskResponse(answer=answer)


@router.post("/stream-document")
async def stream_document(request: Request, body: AskDocumentRequest):
    """Stream tokens about a specific document as SSE events."""
    qa = _get_or_create_qa_service(request, "", include_metadata=False)

    async def event_generator():
        try:
            async for token in qa.stream_about_document(body.question, body.document_id):
                escaped = (
                    token.replace("\\", "\\\\")
                    .replace('"', '\\"')
                    .replace("\n", "\\n")
                )
                yield f'data: {{"token": "{escaped}"}}\n\n'
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("SSE stream error for document: %s", exc, exc_info=True)
            yield 'data: {"error": "Internal error"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
