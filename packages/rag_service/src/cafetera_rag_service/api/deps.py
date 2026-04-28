"""API key authentication dependency for the RAG service."""

from __future__ import annotations

import logging
import secrets

from fastapi import Header, HTTPException, Request

logger = logging.getLogger(__name__)


async def verify_api_key(
    request: Request,
    x_api_key: str = Header("", alias="X-API-Key"),
) -> None:
    """Validate the API key from the X-API-Key header.

    Uses ``secrets.compare_digest`` for constant-time comparison.

    Raises:
        HTTPException: 401 if key is missing or invalid.
    """
    expected_key: str = request.app.state.settings.rag_service_api_key
    if not expected_key:
        # No key configured — skip auth (development mode)
        return
    if not secrets.compare_digest(x_api_key, expected_key):
        logger.warning("Invalid API key attempt")
        raise HTTPException(status_code=401, detail="Invalid API key")
