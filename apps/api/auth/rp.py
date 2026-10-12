"""Hardened OIDC relying party for validating hub-api access tokens.

``penguin_aaa``'s ``OIDCRelyingParty`` validates signature/iss/aud/exp but does not require
``exp``/``iat``/``sub`` to be present, fetches JWKS with unbounded blocking I/O (no size cap,
follows redirects, refetches on every unknown ``kid``), and drops the Nest tier claim. This
subclass closes those gaps with a bounded, single-flight, cooldown-protected async fetch;
``AsgiClaimsAdapter`` bridges the pydantic result to the mapping the ASGI ``TenantMiddleware``
expects. An IdP outage raises ``IdpUnavailableError`` (rendered as 503, never 401).
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import jwt
import structlog
from penguin_aaa.authn.oidc_rp import OIDCRelyingParty, OIDCRPConfig
from penguin_aaa.authn.types import MAX_TOKEN_SIZE, Claims
from penguin_aaa.hardening.validators import validate_https_url

log = structlog.get_logger()

ALLOWED_ALGORITHMS: tuple[str, ...] = ("RS256", "ES256")
REQUIRED_CLAIMS: tuple[str, ...] = ("exp", "iat", "iss", "aud", "sub")
TIER_CLAIM = "https://nest.penguintech.io/tier"
DEFAULT_TIER = "free"
# A resource server never performs a code exchange, so it holds no client secret.
_NO_CLIENT_CREDENTIAL = ""

FETCH_TIMEOUT_S = 5.0
MAX_FETCH_BYTES = 256 * 1024
JWKS_TTL_S = 300.0
# After any IdP fetch attempt, further fetches are refused for this long: a flood of tokens
# carrying random/unknown ``kid`` values costs at most one outbound request per window.
MISS_COOLDOWN_S = 30.0
FAIL_COOLDOWN_S = 5.0

# Set by AsgiClaimsAdapter when verification failed because the IdP was unreachable, so the
# ASGI layer can answer 503 instead of the generic 401.
IDP_OUTAGE: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "nest_idp_outage", default=False
)


class IdpUnavailableError(Exception):
    """The identity provider could not be reached or returned unusable data (-> 503)."""


class UnknownSigningKeyError(ValueError):
    """No JWKS key matches the token's ``kid`` (-> 401)."""


class HardenedRP(OIDCRelyingParty):
    """OIDC RP restricted to RS256/ES256 with mandatory exp/iat/iss/aud/sub and nbf checked.

    The Nest tier claim is carried through in ``ext["tier"]``.
    """

    def __init__(
        self,
        config: OIDCRPConfig,
        *,
        jwks_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create the RP.

        Args:
            config: Issuer/audience/algorithm configuration.
            jwks_url: Known JWKS location; skips OIDC discovery. Must be https (localhost ok).
            transport: Optional httpx transport (tests inject a mock; prod uses the default).
            clock: Monotonic clock used for TTL and cooldowns.
        """
        if set(config.algorithms) - set(ALLOWED_ALGORITHMS):
            raise ValueError(f"hub-api accepts only {ALLOWED_ALGORITHMS}")
        if jwks_url is not None:
            validate_https_url(jwks_url, "OIDC_JWKS_URL")
        super().__init__(config)
        self._jwks_url = jwks_url
        self._transport = transport
        self._clock = clock
        self._keys: dict[str, Any] = {}
        self._keys_fetched_at: float | None = None
        self._last_attempt: float | None = None
        self._last_attempt_ok = True
        self._refresh_lock = asyncio.Lock()

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
            client_secret=_NO_CLIENT_CREDENTIAL,
            redirect_url=issuer,
            algorithms=list(ALLOWED_ALGORITHMS),
        )
        return cls(config, jwks_url=jwks_url)

    async def _fetch_json(self, url: str) -> dict[str, Any]:
        """GET ``url`` as JSON: bounded time and size, no redirects, any failure -> Idp error."""
        try:
            validate_https_url(url, "idp url")
            async with httpx.AsyncClient(
                timeout=FETCH_TIMEOUT_S,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        raise IdpUnavailableError(
                            f"idp returned HTTP {resp.status_code}"
                        )
                    declared = resp.headers.get("content-length")
                    if declared is not None and int(declared) > MAX_FETCH_BYTES:
                        raise IdpUnavailableError("idp response too large")
                    body = bytearray()
                    async for chunk in resp.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_FETCH_BYTES:
                            raise IdpUnavailableError("idp response too large")
            data = json.loads(bytes(body))
        except IdpUnavailableError:
            raise
        except (httpx.HTTPError, ValueError, OSError) as exc:
            raise IdpUnavailableError(
                f"idp fetch failed: {type(exc).__name__}"
            ) from exc
        if not isinstance(data, dict):
            raise IdpUnavailableError("idp returned a non-object document")
        return data

    async def discover(self) -> dict[str, Any]:
        """Fetch and cache the OIDC discovery document (bounded; https-only jwks_uri)."""
        if self._discovery is not None:
            return self._discovery
        url = self._config.issuer_url.rstrip("/") + "/.well-known/openid-configuration"
        document = await self._fetch_json(url)
        required = {"issuer", "jwks_uri", "authorization_endpoint", "token_endpoint"}
        missing = required - set(document)
        if missing:
            raise IdpUnavailableError(
                f"discovery document missing fields: {sorted(missing)}"
            )
        jwks_uri = document["jwks_uri"]
        if not isinstance(jwks_uri, str):
            raise IdpUnavailableError("discovery jwks_uri is not a string")
        try:
            validate_https_url(jwks_uri, "jwks_uri")
        except ValueError as exc:
            raise IdpUnavailableError("discovery jwks_uri is not https") from exc
        self._discovery = document
        return document

    def _cached_key(self, kid: str) -> Any | None:
        """Return the cached key for ``kid`` if the cache is still within its TTL."""
        if self._keys_fetched_at is None:
            return None
        if self._clock() - self._keys_fetched_at >= JWKS_TTL_S:
            return None
        return self._keys.get(kid)

    async def _refresh_keys(self) -> None:
        """Fetch the JWKS once and replace the cache; caller holds the refresh lock."""
        url = self._jwks_url
        if url is None:
            url = str((await self.discover())["jwks_uri"])
        data = await self._fetch_json(url)
        raw_keys = data.get("keys")
        if not isinstance(raw_keys, list):
            raise IdpUnavailableError("jwks document has no keys array")
        keys: dict[str, Any] = {}
        for jwk in raw_keys:
            if not isinstance(jwk, dict) or not isinstance(jwk.get("kid"), str):
                continue
            try:
                keys[jwk["kid"]] = jwt.PyJWK.from_dict(jwk).key
            except (jwt.PyJWTError, ValueError, KeyError):
                log.warning("jwks_key_skipped", kid=jwk["kid"])
        if not keys:
            raise IdpUnavailableError("jwks document has no usable keys")
        self._keys = keys
        self._keys_fetched_at = self._clock()

    async def _signing_key(self, raw_token: str) -> Any:
        """Resolve the verification key for ``raw_token`` without unbounded outbound I/O.

        Cache hit -> no I/O. Miss -> at most one fetch per cooldown window, single-flight
        across concurrent requests. IdP failure -> ``IdpUnavailableError`` (no retry loop).
        """
        kid = jwt.get_unverified_header(raw_token).get("kid")
        if not isinstance(kid, str) or not kid:
            raise UnknownSigningKeyError("token has no kid")
        key = self._cached_key(kid)
        if key is not None:
            return key
        async with self._refresh_lock:
            key = self._cached_key(kid)  # another waiter may have refreshed meanwhile
            if key is not None:
                return key
            now = self._clock()
            window = MISS_COOLDOWN_S if self._last_attempt_ok else FAIL_COOLDOWN_S
            if self._last_attempt is not None and now - self._last_attempt < window:
                if self._last_attempt_ok:
                    raise UnknownSigningKeyError("unknown kid (refresh cooling down)")
                raise IdpUnavailableError("idp recently failed (cooling down)")
            self._last_attempt = now
            try:
                await self._refresh_keys()
            except IdpUnavailableError:
                self._last_attempt_ok = False
                log.warning("idp_unavailable")
                raise
            self._last_attempt_ok = True
            key = self._keys.get(kid)
            if key is None:
                raise UnknownSigningKeyError("unknown kid")
            return key

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
        try:
            claims = await self._rp.validate_token(raw_token)
        except IdpUnavailableError:
            IDP_OUTAGE.set(True)
            raise
        return claims.model_dump()
