"""Shared RS256 test-token minting. One session keypair; imported by conftest and tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

TEST_KID = "test-key-id"
TEST_ISSUER = "https://nest.penguintech.io"
TEST_AUDIENCE = "nest-api"
TIER_CLAIM = "https://nest.penguintech.io/tier"

_state: dict[str, RSAPrivateKey] = {}


def _generate_test_keypair() -> tuple[RSAPrivateKey, RSAPublicKey]:
    """Return the lazily generated session RSA keypair."""
    if "key" not in _state:
        _state["key"] = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
    return _state["key"], _state["key"].public_key()


def mint_claims(
    sub: str,
    tenant: str | None,
    tier: str,
    scopes: list[str] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Build a valid claim set; ``overrides`` replace/add claims, a None value drops one."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "scope": " ".join(["nest:*:admin"] if scopes is None else scopes),
        "iss": TEST_ISSUER,
        "aud": TEST_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        TIER_CLAIM: tier,
    }
    if tenant is not None:
        payload["tenant"] = tenant
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not None}


def _mint_token(
    sub: str, tenant: str, tier: str, scopes: list[str] | None = None, **overrides: Any
) -> str:
    """Mint a valid RS256 JWT (no "Bearer " prefix) with the required claims."""
    private_key, _ = _generate_test_keypair()
    return jwt.encode(
        mint_claims(sub, tenant, tier, scopes, **overrides),
        private_key,
        algorithm="RS256",
        headers={"kid": TEST_KID},
    )
