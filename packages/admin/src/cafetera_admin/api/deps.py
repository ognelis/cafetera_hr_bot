"""FastAPI dependencies for admin endpoints — auth, services, templates."""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from cafetera_admin.config import AdminSettings
from cafetera_core.domain.category_file_service import CategoryFileService
from cafetera_core.domain.document_service import DocumentService
from cafetera_core.domain.qa_service import QAService
from cafetera_core.storage.document_repo import DocumentRepository
from cafetera_core.storage.s3 import S3Storage


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
    """Validate admin cookie.  Raises 403 if invalid or missing."""
    settings = request.app.state.settings
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if admin_session is None or not secrets.compare_digest(
        admin_session, settings.admin_api_key
    ):
        raise HTTPException(status_code=403, detail="Forbidden")


def get_indexing_semaphore(request: Request) -> asyncio.Semaphore:
    return request.app.state.indexing_semaphore


def get_qa_service(request: Request) -> QAService:
    svc = getattr(request.app.state, "qa_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="QA service unavailable")
    return svc


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
QAServiceDep = Annotated[QAService, Depends(get_qa_service)]
CategoryFileServiceDep = Annotated[CategoryFileService, Depends(get_category_file_service)]
