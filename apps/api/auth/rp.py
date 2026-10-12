"""Hardened OIDC relying party for validating hub-api access tokens.

``penguin_aaa``'s ``OIDCRelyingParty`` validates signature/iss/aud/exp but does not require
``exp``/``iat``/``sub`` to be present, resolves JWKS with blocking I/O on the event loop, and drops
the Nest tier claim. This subclass closes those gaps; ``AsgiClaimsAdapter`` bridges the
pydantic result to the mapping the ASGI ``TenantMiddleware`` expects.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any

import jwt
from jwt import PyJWKClient
from penguin_aaa.authn.oidc_rp import OIDCRelyingParty, OIDCRPConfig
from penguin_aaa.authn.types import MAX_TOKEN_SIZE, Claims

ALLOWED_ALGORITHMS: tuple[str, ...] = ("RS256", "ES256")
REQUIRED_CLAIMS: tuple[str, ...] = ("exp", "iat", "iss", "aud", "sub")
TIER_CLAIM = "https://nest.penguintech.io/tier"
DEFAULT_TIER = "free"


class HardenedRP(OIDCRelyingParty):
    """OIDC RP restricted to RS256/ES256 with mandatory exp/iat/iss/aud/sub and nbf checked.

    The Nest tier claim is carried through in ``ext["tier"]``.
    """

    def __init__(self, config: OIDCRPConfig, *, jwks_url: str | None = None) -> None:
        """Create the RP; ``jwks_url`` skips OIDC discovery when the JWKS location is known."""
        if set(config.algorithms) - set(ALLOWED_ALGORITHMS):
            raise ValueError(f"hub-api accepts only {ALLOWED_ALGORITHMS}")
        super().__init__(config)
        self._jwks_url = jwks_url

    @classmethod
    def from_env(cls) -> HardenedRP:
        """Build from OIDC_ISSUER, OIDC_AUDIENCE (default nest-api), OIDC_JWKS_URL (optional)."""
        issuer = os.environ.get("OIDC_ISSUER", "").strip()
        if not issuer:
            raise RuntimeError("OIDC_ISSUER is required to validate access tokens")
        audience = os.environ.get("OIDC_AUDIENCE", "nest-api").strip()
        jwks_url = os.environ.get("OIDC_JWKS_URL", "").strip() or None
        config = OIDCRPConfig(
            issuer_url=issuer,
            client_id=audience,
            client_secret="",  # noqa: S106 - resource server never performs a code exchange
            redirect_url=issuer,
            algorithms=list(ALLOWED_ALGORITHMS),
        )
        return cls(config, jwks_url=jwks_url)

    async def _signing_key(self, raw_token: str) -> Any:
        """Resolve the verification key for ``raw_token`` without blocking the event loop."""
        client = self._jwks_client
        if client is None:
            if self._jwks_url:
                client = PyJWKClient(self._jwks_url)
                self._jwks_client = client
            else:
                await self.discover()
                client = self._jwks_client
        assert client is not None
        signing_key = await asyncio.to_thread(
            client.get_signing_key_from_jwt, raw_token
        )
        return signing_key.key

    async def validate_token(
        self, raw_token: str, expected_nonce: str | None = None
    ) -> Claims:
        """Verify ``raw_token`` and return typed claims; raises on any failure."""
        if expected_nonce is not None:
            raise NotImplementedError("nonce validation is not used for access tokens")
        if len(raw_token) > MAX_TOKEN_SIZE:
            raise ValueError(f"token exceeds {MAX_TOKEN_SIZE} bytes")
        key = await self._signing_key(raw_token)
        payload: dict[str, Any] = jwt.decode(
            raw_token,
            key,
            algorithms=list(ALLOWED_ALGORITHMS),
            audience=self._config.client_id,
            issuer=self._config.issuer_url,
            leeway=int(self._config.clock_skew.total_seconds()),
            options={"require": list(REQUIRED_CLAIMS), "verify_nbf": True},
        )
        tier = payload.get(TIER_CLAIM, DEFAULT_TIER)
        payload["ext"] = {
            "tier": tier if isinstance(tier, str) and tier else DEFAULT_TIER
        }
        for name in ("aud", "scope", "roles", "teams"):
            value = payload.get(name)
            if value is None:
                payload[name] = []
            elif isinstance(value, str):
                payload[name] = value.split() if name == "scope" else [value]
        for name in ("iat", "exp"):
            value = payload.get(name)
            if isinstance(value, int | float):
                payload[name] = datetime.fromtimestamp(value, tz=UTC)
        return Claims.model_validate(payload)


class AsgiClaimsAdapter:
    """Adapt ``HardenedRP`` to the ``verify_token`` contract of ``OIDCAuthMiddleware``.

    The ASGI middlewares read claims as a mapping, so this returns ``Claims.model_dump()``
    (tier under ``ext["tier"]``) instead of the pydantic model.
    """

    def __init__(self, rp: HardenedRP) -> None:
        """Wrap the relying party that performs the actual token validation."""
        self._rp = rp

    async def verify_token(self, raw_token: str) -> dict[str, Any]:
        """Validate ``raw_token`` and return its claims as a plain dict; raises on failure."""
        claims = await self._rp.validate_token(raw_token)
        return claims.model_dump()
