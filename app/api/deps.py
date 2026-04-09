"""FastAPI dependencies for admin endpoints — auth, services, templates."""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import Settings
from app.domain.document_service import DocumentService
from app.domain.qa_service import QAService
from app.storage.document_repo import DocumentRepository
from app.storage.s3 import S3Storage

# Import AppState for typed access - avoid circular import by using TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.main import AppState


def parse_date_range(
    date_from: str | None, date_to: str | None,
) -> tuple[datetime | None, datetime | None]:
    """Parse ISO format date strings to datetime objects."""
    dt_from = None
    dt_to = None
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
        except ValueError:
            pass
    return dt_from, dt_to


def get_settings(request: Request) -> Settings:
    state: AppState = request.app.state  # type: ignore[assignment]
    return state.settings


def get_templates(request: Request) -> Jinja2Templates:
    state: AppState = request.app.state  # type: ignore[assignment]
    return state.templates


def get_doc_repo(request: Request) -> DocumentRepository:
    state: AppState = request.app.state  # type: ignore[assignment]
    return state.doc_repo


def get_doc_service(request: Request) -> DocumentService:
    state: AppState = request.app.state  # type: ignore[assignment]
    service = state.doc_service
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Document service unavailable",
        )
    return service


def get_s3(request: Request) -> S3Storage:
    state: AppState = request.app.state  # type: ignore[assignment]
    s3 = state.s3
    if s3 is None:
        raise HTTPException(
            status_code=503,
            detail="S3 storage unavailable",
        )
    return s3


# ── Auth ──────────────────────────────────────────────────────────

_COOKIE_NAME = "admin_session"


def require_admin(
    request: Request,
    admin_session: Annotated[str | None, Cookie()] = None,
) -> None:
    """Validate admin cookie.  Raises 403 if invalid or missing."""
    state: AppState = request.app.state  # type: ignore[assignment]
    settings = state.settings
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if admin_session is None or not secrets.compare_digest(
        admin_session, settings.admin_api_key
    ):
        raise HTTPException(status_code=403, detail="Forbidden")


def get_indexing_semaphore(request: Request) -> asyncio.Semaphore:
    state: AppState = request.app.state  # type: ignore[assignment]
    return state.indexing_semaphore


def get_qa_service(request: Request) -> QAService:
    state: AppState = request.app.state  # type: ignore[assignment]
    svc = state.qa_service
    if svc is None:
        raise HTTPException(status_code=503, detail="QA service unavailable")
    return svc


AdminDep = Annotated[None, Depends(require_admin)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
TemplatesDep = Annotated[Jinja2Templates, Depends(get_templates)]
RepoDep = Annotated[DocumentRepository, Depends(get_doc_repo)]
ServiceDep = Annotated[DocumentService, Depends(get_doc_service)]
S3Dep = Annotated[S3Storage, Depends(get_s3)]
IndexingSemaphoreDep = Annotated[asyncio.Semaphore, Depends(get_indexing_semaphore)]
QAServiceDep = Annotated[QAService, Depends(get_qa_service)]
