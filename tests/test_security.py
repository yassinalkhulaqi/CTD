"""Tests for the security primitives."""

from __future__ import annotations

import time

import pytest

from ctf_team_dashboard.domain.enums import MemberRole
from ctf_team_dashboard.security.api_keys import (
    generate_api_key,
    hash_secret,
    mask_key,
    split_key,
    verify_api_key,
)
from ctf_team_dashboard.security.passwords import (
    hash_password,
    needs_rehash,
    verify_password,
)
from ctf_team_dashboard.security.permissions import (
    Permission,
    describe_matrix,
    permissions_for,
    role_allows,
)
from ctf_team_dashboard.security.tokens import (
    TokenError,
    decode_token,
    encode_token,
    peek_subject,
    token_expiry,
)


# ----------------------------------------------------------------------
# Passwords
# ----------------------------------------------------------------------
def test_hash_password_produces_verifiable_hash() -> None:
    """A hashed password should verify against the original secret."""
    encoded = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_hash_password_uses_random_salt() -> None:
    """Two hashes of the same password should differ."""
    first = hash_password("same-password")
    second = hash_password("same-password")
    assert first != second


def test_hash_password_rejects_empty_password() -> None:
    """An empty password should be rejected."""
    with pytest.raises(ValueError, match="must not be empty"):
        hash_password("")


def test_verify_password_handles_malformed_hash() -> None:
    """A malformed hash should not raise, only return ``False``."""
    assert not verify_password("secret", "not-a-hash")
    assert not verify_password("secret", "")


def test_needs_rehash_detects_outdated_cost() -> None:
    """Hashes created with fewer iterations should be flagged for upgrade."""
    weak = hash_password("secret-password", iterations=1000)
    assert needs_rehash(weak)
    assert not needs_rehash(hash_password("secret-password"))


# ----------------------------------------------------------------------
# Tokens
# ----------------------------------------------------------------------
def test_encode_and_decode_token_round_trip() -> None:
    """A signed token should decode back to its claims."""
    token = encode_token(
        subject="user-1",
        role="admin",
        secret="top-secret",
        ttl_seconds=60,
        team_id="team-1",
    )
    claims = decode_token(token, secret="top-secret")
    assert claims.subject == "user-1"
    assert claims.role == "admin"
    assert claims.team_id == "team-1"
    assert claims.token_type == "access"


def test_decode_token_rejects_wrong_secret() -> None:
    """A token signed with another secret must be rejected."""
    token = encode_token(subject="u", role="admin", secret="secret-a", ttl_seconds=60)
    with pytest.raises(TokenError, match="signature"):
        decode_token(token, secret="secret-b")


def test_decode_token_rejects_tampered_payload() -> None:
    """Modifying the payload invalidates the signature."""
    token = encode_token(subject="u", role="admin", secret="secret-a", ttl_seconds=60)
    header, _, signature = token.split(".")
    tampered = f"{header}.eyJzdWIiOiJoYWNrZXIifQ.{signature}"
    with pytest.raises(TokenError):
        decode_token(tampered, secret="secret-a")


def test_decode_token_rejects_expired_token() -> None:
    """Expired tokens should be rejected."""
    token = encode_token(
        subject="u", role="admin", secret="secret-a", ttl_seconds=1, issued_at=int(time.time()) - 10
    )
    with pytest.raises(TokenError, match="expired"):
        decode_token(token, secret="secret-a")


def test_decode_token_rejects_malformed_token() -> None:
    """A malformed token should be rejected."""
    with pytest.raises(TokenError, match="malformed"):
        decode_token("not-a-token", secret="secret")


def test_token_expiry_and_peek_subject() -> None:
    """Helper functions should read claims without verification."""
    token = encode_token(subject="user-9", role="lead", secret="s", ttl_seconds=120)
    assert token_expiry(token) > int(time.time())
    assert peek_subject(token) == "user-9"


# ----------------------------------------------------------------------
# API keys
# ----------------------------------------------------------------------
def test_generate_api_key_returns_usable_material() -> None:
    """A generated key should verify against its stored hash."""
    plaintext, prefix, secret_hash = generate_api_key()
    assert plaintext.startswith("ctfd_")
    assert prefix in plaintext
    assert verify_api_key(plaintext, secret_hash)
    assert not verify_api_key("ctfd_bogus_secret", secret_hash)


def test_split_key_rejects_malformed_keys() -> None:
    """Malformed keys should raise a value error."""
    with pytest.raises(ValueError, match="Malformed"):
        split_key("nope")


def test_hash_secret_is_deterministic() -> None:
    """Hashing the same secret should always yield the same digest."""
    assert hash_secret("abc") == hash_secret("abc")
    assert hash_secret("abc") != hash_secret("abd")


def test_mask_key_hides_the_secret() -> None:
    """The masked form should never expose the secret."""
    assert mask_key("abcd1234").endswith("*" * 8)
    assert "abcd1234" in mask_key("abcd1234")


# ----------------------------------------------------------------------
# Permissions
# ----------------------------------------------------------------------
def test_viewer_cannot_create_solves() -> None:
    """The viewer role should be read only."""
    assert not role_allows(MemberRole.VIEWER, Permission.SOLVE_CREATE)
    assert role_allows(MemberRole.VIEWER, Permission.DASHBOARD_VIEW)


def test_analyst_can_create_solves_but_not_manage_teams() -> None:
    """The analyst role should be scoped to recording solves."""
    assert role_allows(MemberRole.ANALYST, Permission.SOLVE_CREATE)
    assert not role_allows(MemberRole.ANALYST, Permission.TEAM_MANAGE)


def test_lead_can_manage_members() -> None:
    """The lead role should manage team members."""
    assert role_allows(MemberRole.LEAD, Permission.MEMBER_MANAGE)
    assert not role_allows(MemberRole.LEAD, Permission.API_KEY_MANAGE)


def test_admin_has_every_permission() -> None:
    """The admin role should hold the full permission set."""
    assert permissions_for(MemberRole.ADMIN) == frozenset(Permission)


def test_describe_matrix_is_serialisable() -> None:
    """The permission matrix should be a list of plain dictionaries."""
    matrix = describe_matrix()
    assert len(matrix) == 4
    assert all(isinstance(entry["permissions"], list) for entry in matrix)
