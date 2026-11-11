"""Security primitives for the CTF Team Dashboard."""

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
    TokenClaims,
    TokenError,
    decode_token,
    encode_token,
)

__all__ = [
    "Permission",
    "TokenClaims",
    "TokenError",
    "decode_token",
    "describe_matrix",
    "encode_token",
    "generate_api_key",
    "hash_password",
    "hash_secret",
    "mask_key",
    "needs_rehash",
    "permissions_for",
    "role_allows",
    "split_key",
    "verify_api_key",
    "verify_password",
]
