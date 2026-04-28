"""FastAPI dependencies for admin endpoints — auth, services, templates."""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from cafetera_admin.config import AdminSettings
from cafetera_admin.domain.document_service import DocumentService
from cafetera_core.domain.category_file_service import CategoryFileService
from cafetera_core.rag_client import RAGClient
from cafetera_core.storage.document_repo import DocumentRepository
from cafetera_core.storage.s3 import S3Storage


class AuthRedirectException(Exception):
    """Raised when an unauthenticated browser/HTMX request hits a protected route."""

    def __init__(self, *, is_htmx: bool = False) -> None:
        self.is_htmx = is_htmx
        super().__init__("Unauthenticated browser/HTMX request")


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


def get_settings(request: Request) -> AdminSettings:
    return request.app.state.settings


def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def get_doc_repo(request: Request) -> DocumentRepository:
    return request.app.state.doc_repo


def get_doc_service(request: Request) -> DocumentService:
    service = getattr(request.app.state, "doc_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Document service unavailable",
        )
    return service


def get_s3(request: Request) -> S3Storage:
    s3 = getattr(request.app.state, "s3", None)
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
    """Validate admin cookie.

    For browser/HTMX requests with missing or invalid credentials, raises
    ``AuthRedirectException`` so the exception handler can redirect to
    ``/login``.  For pure API requests, raises HTTP 403 as before.
    """
    settings = request.app.state.settings
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if admin_session is None or not secrets.compare_digest(
        admin_session, settings.admin_api_key
    ):
        is_htmx = request.headers.get("hx-request") == "true"
        accepts_html = "text/html" in request.headers.get("accept", "")
        if is_htmx or accepts_html:
            raise AuthRedirectException(is_htmx=is_htmx)
        raise HTTPException(status_code=403, detail="Forbidden")


def get_indexing_semaphore(request: Request) -> asyncio.Semaphore:
    return request.app.state.indexing_semaphore


def get_rag_client(request: Request) -> RAGClient:
    client = getattr(request.app.state, "rag_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="RAG service unavailable")
    return client


def get_system_prompt(request: Request) -> str:
    return request.app.state.system_prompt


def get_category_file_service(request: Request) -> CategoryFileService:
    svc = getattr(request.app.state, "category_file_service", None)
    if svc is None:
        raise HTTPException(
            status_code=503,
            detail="Category file service unavailable",
        )
    return svc


AdminDep = Annotated[None, Depends(require_admin)]
SettingsDep = Annotated[AdminSettings, Depends(get_settings)]
TemplatesDep = Annotated[Jinja2Templates, Depends(get_templates)]
RepoDep = Annotated[DocumentRepository, Depends(get_doc_repo)]
ServiceDep = Annotated[DocumentService, Depends(get_doc_service)]
S3Dep = Annotated[S3Storage, Depends(get_s3)]
IndexingSemaphoreDep = Annotated[asyncio.Semaphore, Depends(get_indexing_semaphore)]
RAGClientDep = Annotated[RAGClient, Depends(get_rag_client)]
SystemPromptDep = Annotated[str, Depends(get_system_prompt)]
CategoryFileServiceDep = Annotated[CategoryFileService, Depends(get_category_file_service)]
