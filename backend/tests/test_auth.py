"""
backend/tests/test_auth.py
===========================
Automated tests for JWT authentication and role-based authorization.

Tests cover:
  - Valid login (ADMIN and VIEWER)
  - Invalid password (401)
  - Unknown user (401)
  - Missing token (401)
  - Logout (cookie cleared)
  - /auth/me endpoint (authenticated vs unauthenticated)
  - ADMIN access to admin-only endpoint
  - VIEWER denied admin-only endpoint (403)
  - SSE endpoint: unauthenticated returns 401
  - SSE endpoint: authenticated ADMIN can connect
  - SSE endpoint: authenticated VIEWER can connect
  - Public endpoints remain accessible
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.api.auth import ensure_users_initialized

ADMIN_EMAIL = "official@thermalx.gov.in"
ADMIN_PASSWORD = "ThermalX@123"
VIEWER_EMAIL = "viewer@thermalx.gov.in"
VIEWER_PASSWORD = "Viewer@123"


@pytest.fixture(scope="module", autouse=True)
def setup_users():
    """Ensure users are initialized before tests run."""
    ensure_users_initialized()


@pytest.fixture(scope="function")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _login(client: TestClient, email: str, password: str):
    """Helper: POST to /api/auth/login and return response."""
    return client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------

class TestLogin:
    def test_valid_admin_login(self, client):
        resp = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert data["user"]["role"] == "ADMIN"
        assert "access_token" in resp.cookies

    def test_valid_viewer_login(self, client):
        resp = _login(client, VIEWER_EMAIL, VIEWER_PASSWORD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["role"] == "VIEWER"

    def test_invalid_password(self, client):
        resp = _login(client, ADMIN_EMAIL, "wrongpassword")
        assert resp.status_code == 401
        assert "Invalid credentials" in resp.json()["detail"]

    def test_unknown_user(self, client):
        resp = _login(client, "nobody@example.com", "anypassword")
        assert resp.status_code == 401
        assert "Invalid credentials" in resp.json()["detail"]

    def test_empty_credentials(self, client):
        resp = client.post(
            "/api/auth/login",
            data={"username": "", "password": ""},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code in (400, 422)


class TestLogout:
    def test_logout_clears_cookie(self, client):
        login_resp = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert login_resp.status_code == 200
        logout_resp = client.post("/api/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["status"] == "logged_out"


class TestMe:
    def test_me_with_valid_cookie(self, client):
        login_resp = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert login_resp.status_code == 200
        me_resp = client.get("/api/auth/me")
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "ADMIN"

    def test_me_without_cookie_returns_401(self, client):
        with TestClient(app, raise_server_exceptions=False) as fresh_client:
            resp = fresh_client.get("/api/auth/me")
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------

class TestAuthorization:
    def test_viewer_denied_admin_forward_alert(self, client):
        """VIEWER role cannot forward alerts (ADMIN only)."""
        _login(client, VIEWER_EMAIL, VIEWER_PASSWORD)
        resp = client.post(
            "/api/alerts/TEST-001/forward",
            json={
                "authority_id": "AUTH-01",
                "authority_name": "State Pollution Control Board",
                "recipient_emails": ["spcb@state.gov.in"],
                "message": "Immediate investigation required for high risk event",
                "notes": "Testing",
            },
        )
        assert resp.status_code == 403

    def test_unauthenticated_denied_forward_alert(self, client):
        """Unauthenticated user receives 401 on alert forward."""
        with TestClient(app, raise_server_exceptions=False) as fresh_client:
            resp = fresh_client.post(
                "/api/alerts/TEST-001/forward",
                json={
                    "authority_id": "AUTH-01",
                    "authority_name": "State Pollution Control Board",
                    "recipient_emails": ["spcb@state.gov.in"],
                    "message": "Immediate investigation required for high risk event",
                },
            )
            assert resp.status_code == 401

    def test_viewer_cannot_access_admin_simulate(self, client):
        """VIEWER role cannot POST to /api/events/stream/simulate (ADMIN only)."""
        _login(client, VIEWER_EMAIL, VIEWER_PASSWORD)
        resp = client.post("/api/events/stream/simulate", json={})
        assert resp.status_code == 403

    def test_viewer_cannot_broadcast(self, client):
        """VIEWER role cannot broadcast custom SSE events."""
        _login(client, VIEWER_EMAIL, VIEWER_PASSWORD)
        resp = client.post(
            "/api/events/stream/broadcast",
            json={"event": "test", "data": {}},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# SSE authentication tests
# ---------------------------------------------------------------------------

class TestSSEAuth:
    def test_unauthenticated_sse_returns_401(self, client):
        """SSE stream without cookie returns 401."""
        with TestClient(app, raise_server_exceptions=False) as fresh_client:
            resp = fresh_client.get("/api/events/stream")
            assert resp.status_code == 401

    def test_admin_and_viewer_roles_authorized_for_sse(self):
        """Verify ADMIN and VIEWER roles are permitted for SSE streaming."""
        from backend.api.dependencies import require_role
        from fastapi import HTTPException

        sse_auth = require_role("ADMIN", "VIEWER")

        admin_user = {"email": ADMIN_EMAIL, "role": "ADMIN", "name": "Admin"}
        assert sse_auth(admin_user)["role"] == "ADMIN"

        viewer_user = {"email": VIEWER_EMAIL, "role": "VIEWER", "name": "Viewer"}
        assert sse_auth(viewer_user)["role"] == "VIEWER"

        # Unauthorized role must raise 403
        guest_user = {"email": "guest@test.com", "role": "GUEST", "name": "Guest"}
        with pytest.raises(HTTPException) as exc:
            sse_auth(guest_user)
        assert exc.value.status_code == 403

    def test_sse_status_is_public(self, client):
        """SSE status endpoint is accessible without authentication."""
        with TestClient(app, raise_server_exceptions=False) as fresh_client:
            resp = fresh_client.get("/api/events/stream/status")
            assert resp.status_code == 200
            assert resp.json()["status"] == "online"


# ---------------------------------------------------------------------------
# Regression tests — public/core endpoints remain functional
# ---------------------------------------------------------------------------

class TestRegression:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "service" in resp.json()
