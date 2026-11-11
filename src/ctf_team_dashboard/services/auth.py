"""Authentication and credential management service."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from ctf_team_dashboard.config import Settings, get_settings
from ctf_team_dashboard.domain.enums import EventKind, MemberRole
from ctf_team_dashboard.domain.models import ApiKey, User, utcnow
from ctf_team_dashboard.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.security.api_keys import generate_api_key, split_key, verify_api_key
from ctf_team_dashboard.security.passwords import hash_password, needs_rehash, verify_password
from ctf_team_dashboard.security.permissions import Permission, permissions_for
from ctf_team_dashboard.security.tokens import TokenClaims, decode_token, encode_token

REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller of a request."""

    user_id: str
    username: str
    role: MemberRole
    team_id: str | None
    permissions: frozenset[Permission]
    auth_method: str = "token"

    @property
    def is_anonymous(self) -> bool:
        """Return whether the principal was synthesised for an open API."""
        return self.auth_method == "anonymous"

    def can(self, permission: Permission) -> bool:
        """Return whether the principal holds a permission."""
        return permission in self.permissions


@dataclass(frozen=True, slots=True)
class TokenPair:
    """A freshly minted access and refresh token pair."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"

    def to_payload(self) -> dict[str, str | int]:
        """Return the serialisable representation of the token pair."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "token_type": self.token_type,
        }


@dataclass(frozen=True, slots=True)
class IssuedApiKey:
    """A newly created API key including its one time plaintext value."""

    key: ApiKey
    plaintext: str


def _hash_refresh_token(token: str) -> str:
    """Return the digest stored for a refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    """Business rules for authentication, sessions and API keys."""

    def __init__(
        self,
        repositories: Repositories | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repositories = repositories or Repositories()
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def create_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
        role: MemberRole = MemberRole.VIEWER,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> User:
        """Create a dashboard account."""
        normalised_username = username.strip().lower()
        normalised_email = email.strip().lower()
        if len(normalised_username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
        if "@" not in normalised_email:
            raise ValidationError("Email must be a valid address")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if self.repositories.users.get_by_username(normalised_username) is not None:
            raise ConflictError(f"Username {normalised_username!r} is already taken")
        if self.repositories.users.get_by_email(normalised_email) is not None:
            raise ConflictError(f"Email {normalised_email!r} is already registered")
        if team_id is not None and self.repositories.teams.get(team_id) is None:
            raise NotFoundError(f"Team {team_id!r} does not exist")

        user = User(
            id=user_id or f"user-{uuid.uuid4().hex[:12]}",
            username=normalised_username,
            email=normalised_email,
            password_hash=hash_password(password),
            role=role,
            team_id=team_id,
        )
        self.repositories.users.create(user)
        self.repositories.events.append(
            EventKind.TEAM_UPDATED,
            team_id=team_id,
            payload={"action": "user.created", "username": user.username},
        )
        return user

    def list_users(self) -> list[User]:
        """Return every registered account."""
        return self.repositories.users.list_all()

    def get_user(self, user_id: str) -> User:
        """Return a user or raise :class:`NotFoundError`."""
        user = self.repositories.users.get(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id!r} does not exist")
        return user

    def delete_user(self, user_id: str) -> None:
        """Delete a user and revoke every session it owns."""
        user = self.get_user(user_id)
        self.repositories.sessions.revoke_all_for_user(user_id)
        self.repositories.users.delete(user_id)
        self.repositories.events.append(
            EventKind.TEAM_UPDATED,
            team_id=user.team_id,
            payload={"action": "user.deleted", "username": user.username},
        )

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    def login(
        self, *, username: str, password: str, user_agent: str = ""
    ) -> tuple[User, TokenPair]:
        """Authenticate a user and issue a token pair.

        Args:
            username: The username or email of the account.
            password: The plain text password.
            user_agent: Optional client description stored with the session.

        Returns:
            The authenticated user together with the issued tokens.

        Raises:
            AuthenticationError: When the credentials are invalid.
        """
        candidate = self.repositories.users.get_by_username(username.strip().lower())
        if candidate is None:
            candidate = self.repositories.users.get_by_email(username.strip().lower())
        if candidate is None:
            raise AuthenticationError("Invalid username or password")
        if not candidate.is_active:
            raise AuthenticationError("This account has been disabled")
        if not verify_password(password, candidate.password_hash):
            raise AuthenticationError("Invalid username or password")

        if needs_rehash(candidate.password_hash):
            refreshed = User(
                id=candidate.id,
                username=candidate.username,
                email=candidate.email,
                password_hash=hash_password(password),
                role=candidate.role,
                team_id=candidate.team_id,
                is_active=candidate.is_active,
                created_at=candidate.created_at,
                last_login_at=candidate.last_login_at,
            )
            self.repositories.users.update(refreshed)

        self.repositories.users.record_login(candidate.id)
        pair = self._issue_tokens(candidate, user_agent=user_agent)
        return candidate, pair

    def refresh(self, refresh_token: str) -> TokenPair:
        """Exchange a refresh token for a new token pair.

        Args:
            refresh_token: The refresh token issued at login.

        Returns:
            A freshly issued token pair.

        Raises:
            AuthenticationError: When the token is invalid or expired.
        """
        claims = decode_token(
            refresh_token, secret=self.settings.auth_secret, verify_exp=True
        )
        if claims.token_type != "refresh":
            raise AuthenticationError("A refresh token is required")

        session_id = claims.token_id
        session = self.repositories.sessions.get(session_id)
        if session is None or session["revoked_at"]:
            raise AuthenticationError("Session has been revoked")
        if session["refresh_hash"] != _hash_refresh_token(refresh_token):
            raise AuthenticationError("Session does not match the refresh token")

        user = self.repositories.users.get(claims.subject)
        if user is None or not user.is_active:
            raise AuthenticationError("Account is no longer active")

        self.repositories.sessions.revoke(session_id)
        return self._issue_tokens(user, user_agent=str(session["user_agent"]))

    def logout(self, refresh_token: str) -> None:
        """Revoke the session bound to a refresh token."""
        try:
            claims = decode_token(
                refresh_token, secret=self.settings.auth_secret, verify_exp=False
            )
        except AuthenticationError:
            return
        self.repositories.sessions.revoke(claims.token_id)

    def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke every active session of a user."""
        return self.repositories.sessions.revoke_all_for_user(user_id)

    def _issue_tokens(self, user: User, *, user_agent: str = "") -> TokenPair:
        """Mint an access and refresh token pair for a user."""
        ttl = self.settings.access_token_ttl_seconds
        access_token = encode_token(
            subject=user.id,
            role=user.role.value,
            secret=self.settings.auth_secret,
            ttl_seconds=ttl,
            team_id=user.team_id,
            token_type="access",
        )
        session_id = self._session_id()
        refresh_token = encode_token(
            subject=user.id,
            role=user.role.value,
            secret=self.settings.auth_secret,
            ttl_seconds=REFRESH_TOKEN_TTL_SECONDS,
            team_id=user.team_id,
            token_type="refresh",
            token_id=session_id,
        )
        self.repositories.sessions.create(
            session_id=session_id,
            user_id=user.id,
            refresh_hash=_hash_refresh_token(refresh_token),
            expires_at=utcnow() + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS),
            user_agent=user_agent,
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=ttl)

    @staticmethod
    def _session_id() -> str:
        """Return a fresh, unique session identifier."""
        return f"session-{uuid.uuid4().hex[:24]}"

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    def principal_from_token(self, token: str) -> Principal:
        """Resolve the principal encoded in an access token.

        Args:
            token: The encoded access token.

        Returns:
            The authenticated principal.

        Raises:
            AuthenticationError: When the token is invalid or expired.
        """
        claims = decode_token(token, secret=self.settings.auth_secret, verify_exp=True)
        if claims.token_type != "access":
            raise AuthenticationError("An access token is required")
        return self.principal_from_claims(claims)

    def principal_from_claims(self, claims: TokenClaims) -> Principal:
        """Resolve a principal from already decoded claims."""
        user = self.repositories.users.get(claims.subject)
        if user is None:
            raise AuthenticationError("Account no longer exists")
        if not user.is_active:
            raise AuthenticationError("This account has been disabled")
        role = user.role
        return Principal(
            user_id=user.id,
            username=user.username,
            role=role,
            team_id=user.team_id,
            permissions=permissions_for(role),
            auth_method="token",
        )

    def principal_from_api_key(self, plaintext: str) -> Principal:
        """Resolve the principal bound to an API key.

        Args:
            plaintext: The API key presented by the caller.

        Returns:
            The authenticated principal.

        Raises:
            AuthenticationError: When the key is unknown or revoked.
        """
        try:
            prefix, _ = split_key(plaintext)
        except ValueError as exc:
            raise AuthenticationError("Malformed API key") from exc

        api_key = self.repositories.api_keys.get_by_prefix(prefix)
        if api_key is None or api_key.is_revoked:
            raise AuthenticationError("Unknown or revoked API key")
        if not verify_api_key(plaintext, api_key.secret_hash):
            raise AuthenticationError("Unknown or revoked API key")

        user = self.repositories.users.get(api_key.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Account is no longer active")

        self.repositories.api_keys.touch(api_key.id)
        granted = permissions_for(user.role)
        scoped = frozenset(
            permission
            for permission in granted
            if api_key.allows(permission.value)
        )
        return Principal(
            user_id=user.id,
            username=user.username,
            role=user.role,
            team_id=user.team_id,
            permissions=scoped,
            auth_method="api_key",
        )

    def anonymous_principal(self) -> Principal:
        """Return the synthetic principal used when auth is disabled."""
        return Principal(
            user_id="anonymous",
            username="anonymous",
            role=MemberRole.ADMIN,
            team_id=None,
            permissions=permissions_for(MemberRole.ADMIN),
            auth_method="anonymous",
        )

    # ------------------------------------------------------------------
    # API keys
    # ------------------------------------------------------------------
    def create_api_key(
        self,
        *,
        user_id: str,
        name: str,
        scopes: tuple[str, ...] = (),
    ) -> IssuedApiKey:
        """Create a new API key for a user."""
        user = self.get_user(user_id)
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError("API key name must not be empty")
        plaintext, prefix, secret_hash = generate_api_key()
        api_key = ApiKey(
            id=f"key-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            name=cleaned,
            prefix=prefix,
            secret_hash=secret_hash,
            scopes=tuple(scopes),
        )
        self.repositories.api_keys.create(api_key)
        return IssuedApiKey(key=api_key, plaintext=plaintext)

    def list_api_keys(self, user_id: str) -> list[ApiKey]:
        """Return every key owned by a user."""
        return self.repositories.api_keys.list_for_user(user_id)

    def revoke_api_key(self, user_id: str, key_id: str) -> None:
        """Revoke an API key owned by a user."""
        api_key = self.repositories.api_keys.get(key_id)
        if api_key is None:
            raise NotFoundError(f"API key {key_id!r} does not exist")
        if api_key.user_id != user_id:
            raise PermissionDeniedError("API key belongs to a different account")
        self.repositories.api_keys.revoke(key_id)

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------
    def ensure_bootstrap_admin(
        self, *, username: str = "admin", password: str | None = None
    ) -> User | None:
        """Create the initial administrator account when none exists.

        Returns:
            The created account or ``None`` when users already exist.
        """
        if self.repositories.users.count_matching() > 0:
            return None
        secret = password or self.settings.auth_secret
        return self.create_user(
            username=username,
            email=f"{username}@ctf.local",
            password=secret if len(secret) >= 8 else "changeme123",
            role=MemberRole.ADMIN,
        )


def new_request_id() -> str:
    """Return a random identifier used for request correlation."""
    return secrets.token_hex(8)


def session_expiry() -> datetime:
    """Return the expiry timestamp of a freshly created session."""
    return utcnow() + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS)
