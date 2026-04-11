"""Tests for admin document API — authentication (login, logout, auth guards)."""

from __future__ import annotations

from tests.conftest import TEST_API_KEY

# ── Auth tests ────────────────────────────────────────────────────


class TestAuth:
    def test_login_page_renders(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "HR-панель управления" in resp.text

    def test_login_with_valid_key(self, client):
        resp = client.post(
            "/login",
            data={"api_key": TEST_API_KEY},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/documents"
        assert "admin_session" in resp.cookies

    def test_login_with_invalid_key(self, client):
        resp = client.post(
            "/login",
            data={"api_key": "wrong"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "error=invalid_key" in resp.headers["location"]

    def test_documents_page_requires_auth(self, client):
        resp = client.get("/documents")
        assert resp.status_code == 403

    def test_api_requires_auth(self, client):
        resp = client.get("/api/documents")
        assert resp.status_code == 403

    def test_logout_clears_cookie(self, client, auth_cookies):
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"
