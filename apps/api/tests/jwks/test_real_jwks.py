"""HardenedRP's REAL JWKS/discovery path against an httpx MockTransport (no patched keys)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx
import jwt
import pytest
from app import create_app
from auth import rp as rp_module
from auth.rp import (
    FAIL_COOLDOWN_S,
    FETCH_TIMEOUT_S,
    MAX_FETCH_BYTES,
    MISS_COOLDOWN_S,
    AsgiClaimsAdapter,
    HardenedRP,
    IdpUnavailableError,
    UnknownSigningKeyError,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from penguin_aaa.authn.oidc_rp import OIDCRPConfig

from tests.tokens import (
    TEST_AUDIENCE,
    TEST_ISSUER,
    TEST_KID,
    _generate_test_keypair,
    mint_claims,
)

JWKS_URL = "https://idp.test/jwks"
DISCOVERY_URL = f"{TEST_ISSUER}/.well-known/openid-configuration"
DR = "/api/v1/tenants/t1/data-resources"

Handler = Callable[[httpx.Request], httpx.Response | Any]


class Clock:
    """Controllable monotonic clock."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _jwk(public_key: Any, kid: str) -> dict[str, Any]:
    """Public key as a JWK dict carrying ``kid``."""
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return dict(jwk)


def _jwks_doc(*pairs: tuple[Any, str]) -> dict[str, Any]:
    """JWKS document for (public_key, kid) pairs."""
    return {"keys": [_jwk(k, kid) for k, kid in pairs]}


def _token(kid: str = TEST_KID, key: Any = None) -> str:
    """Valid RS256 token signed by ``key`` (default session key) with header kid ``kid``."""
    signer = key if key is not None else _generate_test_keypair()[0]
    return jwt.encode(
        mint_claims("u", "t1", "free", ["*:read"]),
        signer,
        algorithm="RS256",
        headers={"kid": kid},
    )


def _rp(
    handler: Handler,
    clock: Clock | None = None,
    *,
    jwks_url: str | None = JWKS_URL,
) -> HardenedRP:
    """HardenedRP whose only I/O is the given mock transport."""
    cfg = OIDCRPConfig(
        issuer_url=TEST_ISSUER,
        client_id=TEST_AUDIENCE,
        client_secret="",  # noqa: S106
        redirect_url=TEST_ISSUER,
        algorithms=["RS256", "ES256"],
    )
    return HardenedRP(
        cfg,
        jwks_url=jwks_url,
        transport=httpx.MockTransport(handler),
        clock=clock or Clock(),
    )


def _serving(*pairs: tuple[Any, str]) -> tuple[Handler, list[httpx.Request]]:
    """Handler serving a JWKS, plus the list of requests it has seen."""
    seen: list[httpx.Request] = []
    doc = _jwks_doc(*pairs)

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        await asyncio.sleep(0.01)  # keep the fetch in flight so concurrency is real
        return httpx.Response(200, json=doc)

    return handler, seen


def _good() -> tuple[Handler, list[httpx.Request]]:
    """Handler serving the session test key under TEST_KID."""
    return _serving((_generate_test_keypair()[1], TEST_KID))


async def test_real_fetch_validates_token_and_caches() -> None:
    """The unpatched path fetches the JWKS, verifies the token, and then serves from cache."""
    handler, seen = _good()
    rp = _rp(handler)
    claims = await rp.validate_token(_token())
    assert claims.tenant == "t1"
    await rp.validate_token(_token())
    assert len(seen) == 1
    assert str(seen[0].url) == JWKS_URL


async def test_fetch_uses_bounded_timeout() -> None:
    """Every outbound request carries an explicit timeout <= FETCH_TIMEOUT_S on all phases."""
    timeouts: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeouts.append(request.extensions["timeout"])
        return httpx.Response(
            200, json=_jwks_doc((_generate_test_keypair()[1], TEST_KID))
        )

    await _rp(handler).validate_token(_token())
    assert timeouts and FETCH_TIMEOUT_S <= 5.0
    for phase in ("connect", "read", "write", "pool"):
        assert timeouts[0][phase] == FETCH_TIMEOUT_S


async def test_timeout_surfaces_as_idp_unavailable() -> None:
    """A hung IdP (httpx timeout) is IdpUnavailable, not a verification failure."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(IdpUnavailableError):
        await _rp(handler).validate_token(_token())


async def test_redirect_is_not_followed() -> None:
    """An https->http redirect is never followed (no request to the redirect target)."""
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/jwks"})

    with pytest.raises(IdpUnavailableError):
        await _rp(handler).validate_token(_token())
    assert urls == [JWKS_URL]


def test_http_jwks_url_is_rejected() -> None:
    """A plain-http JWKS URL is refused at construction."""
    handler, _ = _good()
    with pytest.raises(ValueError, match="HTTPS"):
        _rp(handler, jwks_url="http://idp.example/jwks")


def test_from_env_rejects_http_jwks_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """OIDC_JWKS_URL=http://... fails at startup (from_env)."""
    monkeypatch.setenv("OIDC_JWKS_URL", "http://idp.example/jwks")
    with pytest.raises(ValueError, match="HTTPS"):
        HardenedRP.from_env()


@pytest.mark.parametrize(
    "make_response",
    [
        lambda: httpx.Response(500, text="boom"),
        lambda: httpx.Response(200, text="<html>not json</html>"),
        lambda: httpx.Response(200, json=["not", "an", "object"]),
        lambda: httpx.Response(200, json={"keys": "nope"}),
        lambda: httpx.Response(200, json={"keys": []}),
        lambda: httpx.Response(200, content=b"x" * (MAX_FETCH_BYTES + 1)),
        lambda: httpx.Response(
            200, content=b"{}", headers={"content-length": str(MAX_FETCH_BYTES + 1)}
        ),
    ],
    ids=[
        "http500",
        "not_json",
        "not_object",
        "keys_not_list",
        "no_keys",
        "oversize",
        "oversize_cl",
    ],
)
async def test_bad_idp_responses_are_unavailable(
    make_response: Callable[[], httpx.Response],
) -> None:
    """Non-200, malformed, empty or oversized documents never yield a key."""
    rp = _rp(lambda request: make_response())
    with pytest.raises(IdpUnavailableError):
        await rp.validate_token(_token())


async def test_random_kid_flood_costs_one_idp_fetch() -> None:
    """500 unknown kids (concurrent) -> exactly one outbound fetch; known key keeps working."""
    handler, seen = _good()
    clock = Clock()
    rp = _rp(handler, clock)
    await rp.validate_token(_token())  # warm: 1 fetch
    assert len(seen) == 1
    clock.advance(1)

    flood = [_token(kid=f"rand-{i}") for i in range(500)]
    results = await asyncio.gather(
        *(rp.validate_token(t) for t in flood), return_exceptions=True
    )
    assert len(results) == 500
    assert all(isinstance(r, UnknownSigningKeyError) for r in results)
    assert len(seen) == 1  # still inside the miss cooldown: zero new fetches

    await rp.validate_token(_token())  # cached known key unaffected
    assert len(seen) == 1


async def test_cooldown_expiry_allows_rotation_pickup() -> None:
    """After the cooldown a new kid triggers exactly one refresh and then validates."""
    old_pub = _generate_test_keypair()[1]
    new_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    docs: list[dict[str, Any]] = [_jwks_doc((old_pub, TEST_KID))]
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append("fetch")
        return httpx.Response(200, json=docs[0])

    clock = Clock()
    rp = _rp(handler, clock)
    await rp.validate_token(_token())
    docs[0] = _jwks_doc((old_pub, TEST_KID), (new_priv.public_key(), "rotated"))

    with pytest.raises(UnknownSigningKeyError):
        await rp.validate_token(_token("rotated", new_priv))  # cooling down
    assert len(seen) == 1

    clock.advance(MISS_COOLDOWN_S + 1)
    claims = await rp.validate_token(_token("rotated", new_priv))
    assert claims.tenant == "t1"
    assert len(seen) == 2


async def test_concurrent_cold_start_is_single_flight() -> None:
    """20 simultaneous first requests share one in-flight JWKS fetch."""
    handler, seen = _good()
    rp = _rp(handler)
    results = await asyncio.gather(*(rp.validate_token(_token()) for _ in range(20)))
    assert len(results) == 20
    assert len(seen) == 1


async def test_outage_is_not_retried_inside_cooldown() -> None:
    """A down IdP gets one attempt per FAIL cooldown, however many requests arrive."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("down", request=request)

    clock = Clock()
    rp = _rp(handler, clock)
    results = await asyncio.gather(
        *(rp.validate_token(_token()) for _ in range(30)), return_exceptions=True
    )
    assert len(results) == 30
    assert all(isinstance(r, IdpUnavailableError) for r in results)
    assert len(calls) == 1
    with pytest.raises(IdpUnavailableError):
        await rp.validate_token(_token())
    assert len(calls) == 1
    clock.advance(FAIL_COOLDOWN_S + 1)
    with pytest.raises(IdpUnavailableError):
        await rp.validate_token(_token())
    assert len(calls) == 2


async def test_discovery_path_is_bounded_and_https_only() -> None:
    """Without OIDC_JWKS_URL, discovery runs through the same bounded fetch."""
    pub = _generate_test_keypair()[1]
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url) == DISCOVERY_URL:
            return httpx.Response(
                200,
                json={
                    "issuer": TEST_ISSUER,
                    "jwks_uri": JWKS_URL,
                    "authorization_endpoint": f"{TEST_ISSUER}/auth",
                    "token_endpoint": f"{TEST_ISSUER}/token",
                },
            )
        return httpx.Response(200, json=_jwks_doc((pub, TEST_KID)))

    rp = _rp(handler, jwks_url=None)
    assert (await rp.validate_token(_token())).tenant == "t1"
    assert seen == [DISCOVERY_URL, JWKS_URL]


@pytest.mark.parametrize(
    "doc",
    [
        {
            "issuer": TEST_ISSUER,
            "jwks_uri": "http://idp.example/jwks",
            "authorization_endpoint": "a",
            "token_endpoint": "t",
        },
        {"issuer": TEST_ISSUER},
    ],
    ids=["http_jwks_uri", "missing_fields"],
)
async def test_bad_discovery_documents_are_unavailable(doc: dict[str, Any]) -> None:
    """A discovery doc pointing at plain http, or missing fields, is rejected."""
    rp = _rp(lambda request: httpx.Response(200, json=doc), jwks_url=None)
    with pytest.raises(IdpUnavailableError):
        await rp.validate_token(_token())


async def test_unknown_kid_without_cache_is_401_class_not_503() -> None:
    """IdP up but kid absent -> UnknownSigningKeyError (a ValueError => 401), not outage."""
    handler, _ = _good()
    with pytest.raises(UnknownSigningKeyError):
        await _rp(handler).validate_token(_token(kid="nope"))


def _stack_client(rp: HardenedRP) -> Any:
    """Full-stack client using the real (unpatched) RP."""
    return create_app(rp=AsgiClaimsAdapter(rp)).test_client()


def _hdr(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


async def test_stack_valid_token_through_real_jwks_is_200() -> None:
    """End to end over ASGI with the real key fetch."""
    handler, _ = _good()
    r = await _stack_client(_rp(handler)).get(DR, headers=_hdr(_token()))
    assert r.status_code == 200


async def test_stack_idp_outage_is_503_with_retry_after_not_401() -> None:
    """IdP down -> 503 + Retry-After; the flag does not leak into the next request's 401."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    client = _stack_client(_rp(handler))
    r = await client.get(DR, headers=_hdr(_token()))
    assert r.status_code == 503
    assert r.headers["retry-after"] == "5"
    assert json.loads(await r.get_data()) == {"error": "Identity provider unavailable"}

    bad = await client.get(DR, headers=_hdr("not.a.jwt"))
    assert bad.status_code == 401  # outage flag reset per request
    assert (await client.get(DR)).status_code == 401  # no token: still 401


async def test_stack_unknown_kid_is_401_while_idp_is_up() -> None:
    """A token with an unknown kid is rejected 401 (not 503) when the IdP is healthy."""
    handler, _ = _good()
    r = await _stack_client(_rp(handler)).get(DR, headers=_hdr(_token(kid="stranger")))
    assert r.status_code == 401


def test_module_exposes_bounds() -> None:
    """Pin the safety constants so a loosening shows up in review."""
    assert FETCH_TIMEOUT_S <= 5.0
    assert MAX_FETCH_BYTES <= 256 * 1024
    assert MISS_COOLDOWN_S >= 30.0
    assert rp_module.FAIL_COOLDOWN_S >= 1.0
