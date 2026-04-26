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

    def test_documents_page_redirects_to_login_for_browser(self, client):
        """Browser requests (Accept: text/html) should get 303 redirect to /login."""
        resp = client.get("/documents", headers={"Accept": "text/html"}, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    def test_documents_page_redirects_via_htmx(self, client):
        """HTMX requests should get 200 with HX-Redirect header."""
        resp = client.get("/documents", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        assert resp.headers.get("hx-redirect") == "/login"

    def test_api_requires_auth_returns_403(self, client):
        """Pure API requests (no Accept: text/html, no HX-Request) should still get 403."""
        resp = client.get("/api/documents")
        assert resp.status_code == 403

    def test_category_files_redirects_to_login_for_browser(self, client):
        """Browser requests to category-files should redirect to /login."""
        resp = client.get(
            "/category-files",
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    def test_logout_clears_cookie(self, client, auth_cookies):
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"
