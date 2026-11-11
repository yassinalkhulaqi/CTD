"""Authentication endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from ctf_team_dashboard.dependencies import (
    AuthServiceDep,
    PrincipalDep,
    SettingsDep,
    describe_principal,
    user_agent,
)
from ctf_team_dashboard.domain.enums import MemberRole
from ctf_team_dashboard.schemas import (
    ApiKeyCreate,
    ApiKeyRead,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    SessionRead,
    TokenPairRead,
    UserRead,
)
from ctf_team_dashboard.security.permissions import Permission, describe_matrix, permissions_for

router = APIRouter(tags=["auth"])


def _user_read(user: object) -> UserRead:
    """Map a domain user onto its API representation."""
    return UserRead(
        id=user.id,  # type: ignore[attr-defined]
        username=user.username,  # type: ignore[attr-defined]
        email=user.email,  # type: ignore[attr-defined]
        role=user.role,  # type: ignore[attr-defined]
        team_id=user.team_id,  # type: ignore[attr-defined]
        is_active=user.is_active,  # type: ignore[attr-defined]
        created_at=user.created_at,  # type: ignore[attr-defined]
        last_login_at=user.last_login_at,  # type: ignore[attr-defined]
    )


@router.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, service: AuthServiceDep) -> LoginResponse:
    """Authenticate with a username (or email) and password."""
    user, tokens = service.login(
        username=payload.username,
        password=payload.password,
        user_agent=user_agent(request),
    )
    return LoginResponse(
        user=_user_read(user),
        tokens=TokenPairRead(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            token_type=tokens.token_type,
        ),
        permissions=sorted(permission.value for permission in permissions_for(user.role)),
    )


@router.post("/api/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, service: AuthServiceDep) -> UserRead:
    """Register a new dashboard account."""
    user = service.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        role=MemberRole.VIEWER,
        team_id=payload.team_id,
    )
    return _user_read(user)


@router.post("/api/auth/refresh", response_model=TokenPairRead)
def refresh(payload: RefreshRequest, service: AuthServiceDep) -> TokenPairRead:
    """Exchange a refresh token for a new token pair."""
    tokens = service.refresh(payload.refresh_token)
    return TokenPairRead(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        token_type=tokens.token_type,
    )


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, service: AuthServiceDep) -> None:
    """Revoke the session bound to a refresh token."""
    service.logout(payload.refresh_token)


@router.get("/api/auth/me", response_model=dict[str, object])
def me(principal: PrincipalDep) -> dict[str, object]:
    """Return the profile of the authenticated caller."""
    return describe_principal(principal)


@router.get("/api/auth/permissions", response_model=list[dict[str, object]])
def permissions_matrix() -> list[dict[str, object]]:
    """Return the role to permission matrix used by the UI."""
    return describe_matrix()


@router.get("/api/auth/api-keys", response_model=list[ApiKeyRead])
def list_api_keys(user_id: str, service: AuthServiceDep) -> list[ApiKeyRead]:
    """Return the API keys owned by a user."""
    keys = service.list_api_keys(user_id)
    return [
        ApiKeyRead(
            id=key.id,
            user_id=key.user_id,
            name=key.name,
            prefix=key.prefix,
            masked=key.masked,
            scopes=list(key.scopes),
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            revoked_at=key.revoked_at,
        )
        for key in keys
    ]


@router.post(
    "/api/auth/api-keys",
    response_model=dict[str, object],
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(payload: ApiKeyCreate, service: AuthServiceDep) -> dict[str, object]:
    """Create an API key and return its plaintext value once."""
    issued = service.create_api_key(
        user_id=payload.user_id,
        name=payload.name,
        scopes=tuple(payload.scopes),
    )
    return {
        "key": ApiKeyRead(
            id=issued.key.id,
            user_id=issued.key.user_id,
            name=issued.key.name,
            prefix=issued.key.prefix,
            masked=issued.key.masked,
            scopes=list(issued.key.scopes),
            created_at=issued.key.created_at,
            last_used_at=issued.key.last_used_at,
            revoked_at=issued.key.revoked_at,
        ).model_dump(mode="json"),
        "plaintext": issued.plaintext,
    }


@router.delete("/api/auth/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: str, user_id: str, service: AuthServiceDep) -> None:
    """Revoke an API key."""
    service.revoke_api_key(user_id, key_id)


@router.get("/api/auth/sessions", response_model=list[SessionRead])
def list_sessions(user_id: str, service: AuthServiceDep) -> list[SessionRead]:
    """Return the active sessions of a user."""
    sessions = service.repositories.sessions.list_for_user(user_id)
    return [
        SessionRead(
            id=str(session["id"]),
            user_id=str(session["user_id"]),
            created_at=session["created_at"],
            expires_at=session["expires_at"],
            revoked_at=session["revoked_at"],
            user_agent=str(session["user_agent"]),
        )
        for session in sessions
    ]


@router.get("/api/auth/config", response_model=dict[str, object])
def auth_config(settings: SettingsDep) -> dict[str, object]:
    """Return the authentication capabilities exposed by the server."""
    return {
        "enabled": settings.auth_enabled,
        "access_token_ttl_seconds": settings.access_token_ttl_seconds,
        "permissions": sorted(permission.value for permission in Permission),
    }
