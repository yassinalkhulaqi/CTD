"""FastAPI dependencies enforcing authentication and authorisation."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status

from ctf_team_dashboard.config import Settings, get_settings
from ctf_team_dashboard.errors import AuthenticationError, PermissionDeniedError
from ctf_team_dashboard.security.permissions import Permission
from ctf_team_dashboard.services.auth import AuthService, Principal


def get_auth_service() -> AuthService:
    """Dependency returning the authentication service."""
    return AuthService()


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _extract_credentials(request: Request) -> tuple[str | None, str | None]:
    """Return the bearer token and API key carried by a request."""
    header = request.headers.get("authorization")
    api_key = request.headers.get("x-api-key")
    token: str | None = None
    if header:
        scheme, _, value = header.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            token = value.strip()
    return token, api_key.strip() if api_key else None


def get_current_principal(
    request: Request,
    service: AuthServiceDep,
    settings: SettingsDep,
) -> Principal:
    """Resolve the principal performing the current request.

    When authentication is disabled the API operates in an open mode and a
    synthetic administrator principal is returned so that the dashboard stays
    usable for public scoreboards.

    Args:
        request: The incoming request.
        service: The authentication service.
        settings: The resolved application settings.

    Returns:
        The authenticated principal.

    Raises:
        AuthenticationError: When credentials are missing or invalid.
    """
    if not settings.auth_enabled:
        return service.anonymous_principal()

    token, api_key = _extract_credentials(request)
    if api_key:
        return service.principal_from_api_key(api_key)
    if token:
        return service.principal_from_token(token)

    raise AuthenticationError("Authentication credentials are required")


PrincipalDep = Annotated[Principal, Depends(get_current_principal)]


def require_permission(
    *permissions: Permission,
) -> Callable[[Principal], Coroutine[None, None, Principal]]:
    """Build a dependency that enforces one or more permissions.

    Args:
        *permissions: The permissions the caller must hold. Any one of them
            is sufficient when several are supplied.

    Returns:
        A FastAPI dependency callable.
    """
    required = frozenset(permissions)

    async def dependency(principal: PrincipalDep) -> Principal:
        """Validate the permissions of the current principal."""
        if not required:
            return principal
        if any(principal.can(permission) for permission in required):
            return principal
        names = ", ".join(sorted(permission.value for permission in required))
        raise PermissionDeniedError(f"The operation requires one of: {names}")

    return dependency


def require_role(
    *roles: str,
) -> Callable[[Principal], Coroutine[None, None, Principal]]:
    """Build a dependency that enforces one of the accepted roles.

    Args:
        *roles: The accepted role names.

    Returns:
        A FastAPI dependency callable.
    """

    async def dependency(principal: PrincipalDep) -> Principal:
        """Validate the role of the current principal."""
        if not roles:
            return principal
        if principal.role.value in roles:
            return principal
        raise PermissionDeniedError(
            f"The operation requires one of the roles: {', '.join(sorted(roles))}"
        )

    return dependency


def require_authenticated(principal: PrincipalDep) -> Principal:
    """Dependency rejecting anonymous callers when auth is enabled."""
    if principal.is_anonymous:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required for this operation",
        )
    return principal


def client_ip(request: Request) -> str:
    """Return the best guess client address for a request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def user_agent(request: Request) -> str:
    """Return the user agent header of a request."""
    return request.headers.get("user-agent", "")[:512]


def describe_principal(principal: Principal) -> dict[str, Any]:
    """Return a serialisable description of a principal."""
    return {
        "user_id": principal.user_id,
        "username": principal.username,
        "role": principal.role.value,
        "team_id": principal.team_id,
        "auth_method": principal.auth_method,
        "permissions": sorted(permission.value for permission in principal.permissions),
    }
