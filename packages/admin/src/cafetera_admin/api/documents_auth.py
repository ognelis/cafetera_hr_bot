"""Document admin auth routes — login, logout, root redirect."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse

from cafetera_admin.api.deps import SettingsDep, TemplatesDep
from cafetera_admin.api.documents_helpers import _COOKIE_NAME

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    templates: TemplatesDep,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": error},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    settings: SettingsDep,
    api_key: Annotated[str, Form()],
):
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if not secrets.compare_digest(api_key, settings.admin_api_key):
        return RedirectResponse(
            url="/login?error=invalid_key", status_code=303
        )
    response = RedirectResponse(url="/documents", status_code=303)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=settings.admin_api_key,
        httponly=True,
        samesite="strict",
        max_age=60 * 60 * 24,  # 24 hours
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key=_COOKIE_NAME)
    return response


@router.get("/")
async def root_redirect(
    request: Request,
    settings: SettingsDep,
    admin_session: Annotated[str | None, Cookie()] = None,
):
    """Redirect to /documents if authenticated, otherwise to /login."""
    if settings.admin_api_key and admin_session is not None:
        if secrets.compare_digest(admin_session, settings.admin_api_key):
            return RedirectResponse(url="/documents", status_code=303)
    return RedirectResponse(url="/login", status_code=303)
