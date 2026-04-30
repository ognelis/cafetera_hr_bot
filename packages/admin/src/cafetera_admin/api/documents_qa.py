"""QA / streaming endpoints — ask questions about documents."""

from __future__ import annotations

import asyncio
import logging

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)
from starlette.responses import StreamingResponse

from cafetera_admin.api.deps import (
    AdminDep,
    RAGClientDep,
    RepoDep,
    SystemPromptDep,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/qa/ask-global")
async def ask_global_question(
    _: AdminDep,
    rag_client: RAGClientDep,
    system_prompt: SystemPromptDep,
    question: str = Query(..., min_length=1, max_length=1000),
):
    """Ask a question across the entire knowledge base. Returns SSE stream."""

    async def event_generator():
        """Generate SSE events with tokens from the LLM."""
        try:
            async for token in rag_client.stream_ask(
                question, system_prompt=system_prompt, include_metadata=True
            ):
                escaped_token = token.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                yield f'data: {{"token": "{escaped_token}"}}\n\n'
            yield 'data: {"done": true}\n\n'
        except asyncio.CancelledError:
            logger.info("Client disconnected during global question stream")
            return
        except Exception as exc:
            logger.error("Error in SSE stream for global question: %s", exc, exc_info=True)
            yield 'data: {"error": "Ошибка при получении ответа"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/api/documents/{document_id}/ask")
async def ask_about_document(
    document_id: str,
    _auth: AdminDep,
    repo: RepoDep,
    rag_client: RAGClientDep,
    question: str = Query(..., min_length=1, max_length=1000),
):
    """Ask a question about a specific document. Returns SSE stream."""
    doc = await repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if doc.status.value != "completed":
        raise HTTPException(status_code=400, detail="Документ не готов для вопросов")

    async def event_generator():
        """Generate SSE events with tokens from the LLM."""
        try:
            async for token in rag_client.stream_about_document(question, document_id):
                # Escape newlines and quotes for JSON serialization
                escaped_token = token.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                yield f'data: {{"token": "{escaped_token}"}}\n\n'
            yield 'data: {"done": true}\n\n'
        except asyncio.CancelledError:
            logger.info("Client disconnected during document %s question stream", document_id)
            return
        except Exception as exc:
            logger.error("Error in SSE stream for document %s: %s", document_id, exc, exc_info=True)
            yield 'data: {"error": "Ошибка при получении ответа"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
