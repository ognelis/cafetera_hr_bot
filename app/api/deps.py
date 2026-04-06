"""FastAPI dependencies for admin endpoints — auth, services, templates."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import Settings
from app.domain.document_service import DocumentService
from app.storage.document_repo import DocumentRepository
from app.storage.s3 import S3Storage


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def get_doc_repo(request: Request) -> DocumentRepository:
    return request.app.state.doc_repo


def get_doc_service(request: Request) -> DocumentService:
    service = request.app.state.doc_service
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Document service unavailable",
        )
    return service


def get_s3(request: Request) -> S3Storage:
    s3 = request.app.state.s3
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
    settings: Settings = request.app.state.settings
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if admin_session is None or not secrets.compare_digest(
        admin_session, settings.admin_api_key
    ):
        raise HTTPException(status_code=403, detail="Forbidden")


AdminDep = Annotated[None, Depends(require_admin)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
TemplatesDep = Annotated[Jinja2Templates, Depends(get_templates)]
RepoDep = Annotated[DocumentRepository, Depends(get_doc_repo)]
ServiceDep = Annotated[DocumentService, Depends(get_doc_service)]
S3Dep = Annotated[S3Storage, Depends(get_s3)]
