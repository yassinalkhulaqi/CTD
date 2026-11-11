"""Tests for the authentication service and the auth API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.config import Settings
from ctf_team_dashboard.domain.enums import MemberRole
from ctf_team_dashboard.errors import AuthenticationError, ConflictError, ValidationError
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.security.permissions import Permission
from ctf_team_dashboard.services.auth import AuthService


@pytest.fixture
def auth_service(repositories: Repositories, settings: Settings) -> AuthService:
    """Return an auth service bound to the isolated test database."""
    return AuthService(repositories, settings)


def test_create_user_requires_strong_password(
    auth_service: AuthService,
) -> None:
    """Short passwords should be rejected."""
    with pytest.raises(ValidationError, match="at least 8 characters"):
        auth_service.create_user(username="alice", email="alice@example.com", password="short")


def test_create_user_rejects_duplicate_username(auth_service: AuthService) -> None:
    """Usernames must be unique."""
    auth_service.create_user(
        username="alice", email="alice@example.com", password="password123"
    )
    with pytest.raises(ConflictError, match="Username"):
        auth_service.create_user(
            username="alice", email="other@example.com", password="password123"
        )


def test_create_user_rejects_invalid_email(auth_service: AuthService) -> None:
    """Emails must look like addresses."""
    with pytest.raises(ValidationError, match="valid address"):
        auth_service.create_user(username="alice", email="not-an-email", password="password123")


def test_login_succeeds_with_valid_credentials(auth_service: AuthService) -> None:
    """Valid credentials should return a token pair."""
    auth_service.create_user(
        username="alice", email="alice@example.com", password="password123"
    )
    user, tokens = auth_service.login(username="alice", password="password123")
    assert user.username == "alice"
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.expires_in > 0


def test_login_rejects_wrong_password(auth_service: AuthService) -> None:
    """Invalid credentials should raise an authentication error."""
    auth_service.create_user(
        username="alice", email="alice@example.com", password="password123"
    )
    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        auth_service.login(username="alice", password="nope")


def test_login_rejects_unknown_user(auth_service: AuthService) -> None:
    """Unknown users should raise a generic authentication error."""
    with pytest.raises(AuthenticationError):
        auth_service.login(username="ghost", password="password123")


def test_refresh_rotates_the_refresh_token(auth_service: AuthService) -> None:
    """Refreshing should issue a new pair and invalidate the old refresh token."""
    auth_service.create_user(
        username="alice", email="alice@example.com", password="password123"
    )
    _, tokens = auth_service.login(username="alice", password="password123")
    rotated = auth_service.refresh(tokens.refresh_token)
    assert rotated.refresh_token != tokens.refresh_token
    with pytest.raises(AuthenticationError, match="revoked"):
        auth_service.refresh(tokens.refresh_token)


def test_refresh_rejects_access_token(auth_service: AuthService) -> None:
    """An access token must not be usable as a refresh token."""
    auth_service.create_user(
        username="alice", email="alice@example.com", password="password123"
    )
    _, tokens = auth_service.login(username="alice", password="password123")
    with pytest.raises(AuthenticationError, match="refresh token is required"):
        auth_service.refresh(tokens.access_token)


def test_logout_revokes_the_session(auth_service: AuthService) -> None:
    """Logging out should invalidate the refresh token."""
    auth_service.create_user(
        username="alice", email="alice@example.com", password="password123"
    )
    _, tokens = auth_service.login(username="alice", password="password123")
    auth_service.logout(tokens.refresh_token)
    with pytest.raises(AuthenticationError, match="revoked"):
        auth_service.refresh(tokens.refresh_token)


def test_principal_from_token_carries_permissions(auth_service: AuthService) -> None:
    """A decoded token should resolve to a principal with permissions."""
    user = auth_service.create_user(
        username="alice",
        email="alice@example.com",
        password="password123",
        role=MemberRole.LEAD,
    )
    _, tokens = auth_service.login(username="alice", password="password123")
    principal = auth_service.principal_from_token(tokens.access_token)
    assert principal.user_id == user.id
    assert principal.role is MemberRole.LEAD
    assert principal.can(Permission.CHALLENGE_CREATE)


def test_api_key_principal_is_scoped(auth_service: AuthService) -> None:
    """API keys should authenticate and resolve their owner."""
    user = auth_service.create_user(
        username="alice", email="alice@example.com", password="password123"
    )
    issued = auth_service.create_api_key(user_id=user.id, name="CI")
    principal = auth_service.principal_from_api_key(issued.plaintext)
    assert principal.user_id == user.id
    assert principal.auth_method == "api_key"


def test_revoked_api_key_is_rejected(auth_service: AuthService) -> None:
    """Revoked keys should no longer authenticate."""
    user = auth_service.create_user(
        username="alice", email="alice@example.com", password="password123"
    )
    issued = auth_service.create_api_key(user_id=user.id, name="CI")
    auth_service.revoke_api_key(user.id, issued.key.id)
    with pytest.raises(AuthenticationError, match="Unknown or revoked"):
        auth_service.principal_from_api_key(issued.plaintext)


def test_ensure_bootstrap_admin_creates_once(auth_service: AuthService) -> None:
    """The bootstrap admin should only be created when no users exist."""
    created = auth_service.ensure_bootstrap_admin(password="adminpassword")
    assert created is not None
    assert auth_service.ensure_bootstrap_admin(password="adminpassword") is None


def test_login_endpoint_returns_tokens(client: TestClient) -> None:
    """The login endpoint should return a user and token pair."""
    client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "password123"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["username"] == "alice"
    assert payload["tokens"]["access_token"]
    assert "challenge:view" in payload["permissions"]


def test_login_endpoint_rejects_bad_password(client: TestClient) -> None:
    """Invalid credentials should return the error envelope."""
    client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_auth_config_reports_enabled_state(client: TestClient) -> None:
    """The auth config endpoint should describe the server capabilities."""
    response = client.get("/api/auth/config")
    assert response.status_code == 200
    assert "enabled" in response.json()


def test_permissions_matrix_endpoint(client: TestClient) -> None:
    """The permissions endpoint should expose the role matrix."""
    response = client.get("/api/auth/permissions")
    assert response.status_code == 200
    assert len(response.json()) == 4
