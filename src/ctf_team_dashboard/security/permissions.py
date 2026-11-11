"""Permission catalogue and role mapping for role based access control."""

from __future__ import annotations

from enum import Enum

from ctf_team_dashboard.domain.enums import MemberRole


class Permission(str, Enum):
    """Every capability that can be granted to a dashboard user."""

    DASHBOARD_VIEW = "dashboard:view"
    STATS_VIEW = "stats:view"
    TEAM_VIEW = "team:view"
    TEAM_MANAGE = "team:manage"
    MEMBER_VIEW = "member:view"
    MEMBER_MANAGE = "member:manage"
    CHALLENGE_VIEW = "challenge:view"
    CHALLENGE_CREATE = "challenge:create"
    CHALLENGE_UPDATE = "challenge:update"
    CHALLENGE_DELETE = "challenge:delete"
    SOLVE_VIEW = "solve:view"
    SOLVE_CREATE = "solve:create"
    SOLVE_DELETE = "solve:delete"
    API_KEY_MANAGE = "api_key:manage"
    AUDIT_VIEW = "audit:view"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def parse(cls, raw: str) -> Permission:
        """Parse a permission value.

        Args:
            raw: The raw permission string.

        Returns:
            The matching permission.

        Raises:
            ValueError: When the permission is unknown.
        """
        normalised = raw.strip().lower()
        for member in cls:
            if member.value == normalised:
                return member
        raise ValueError(f"{raw!r} is not a valid Permission")


_VIEWER: frozenset[Permission] = frozenset(
    {
        Permission.DASHBOARD_VIEW,
        Permission.STATS_VIEW,
        Permission.TEAM_VIEW,
        Permission.MEMBER_VIEW,
        Permission.CHALLENGE_VIEW,
        Permission.SOLVE_VIEW,
    }
)

_ANALYST: frozenset[Permission] = _VIEWER | frozenset(
    {
        Permission.SOLVE_CREATE,
    }
)

_LEAD: frozenset[Permission] = _ANALYST | frozenset(
    {
        Permission.CHALLENGE_CREATE,
        Permission.CHALLENGE_UPDATE,
        Permission.MEMBER_MANAGE,
        Permission.SOLVE_DELETE,
    }
)

_ADMIN: frozenset[Permission] = _LEAD | frozenset(
    {
        Permission.CHALLENGE_DELETE,
        Permission.TEAM_MANAGE,
        Permission.API_KEY_MANAGE,
        Permission.AUDIT_VIEW,
    }
)

ROLE_PERMISSIONS: dict[MemberRole, frozenset[Permission]] = {
    MemberRole.VIEWER: _VIEWER,
    MemberRole.ANALYST: _ANALYST,
    MemberRole.LEAD: _LEAD,
    MemberRole.ADMIN: _ADMIN,
}


def permissions_for(role: MemberRole) -> frozenset[Permission]:
    """Return every permission granted to a role.

    Args:
        role: The role to resolve.

    Returns:
        The immutable set of granted permissions.
    """
    return ROLE_PERMISSIONS.get(role, _VIEWER)


def role_allows(role: MemberRole, permission: Permission) -> bool:
    """Return whether a role grants the requested permission."""
    return permission in permissions_for(role)


def describe_matrix() -> list[dict[str, object]]:
    """Return a serialisable description of the role/permission matrix."""
    return [
        {
            "role": role.value,
            "permissions": sorted(permission.value for permission in permissions),
        }
        for role, permissions in ROLE_PERMISSIONS.items()
    ]
