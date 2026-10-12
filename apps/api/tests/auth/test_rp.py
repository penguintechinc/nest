"""Token-validation hardening, exercised end to end through the ASGI stack."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import jwt
import pytest
from app import create_app
from auth.rp import HardenedRP
from cryptography.hazmat.primitives import serialization

from tests.tokens import (
    TEST_AUDIENCE,
    TEST_ISSUER,
    TEST_KID,
    _generate_test_keypair,
    _mint_token,
    mint_claims,
)

URL = "/api/v1/tenants/t1/data-resources"


def _hdr(tok: str) -> dict[str, str]:
    """Authorization header for ``tok``."""
    return {"Authorization": f"Bearer {tok}"}


def _signed(**overrides: Any) -> str:
    """RS256 token over valid claims with ``overrides`` applied (None drops a claim)."""
    claims = {**mint_claims("u", "t1", "free", ["*:read"]), **overrides}
    return jwt.encode(
        {k: v for k, v in claims.items() if v is not None},
        _generate_test_keypair()[0],
        algorithm="RS256",
        headers={"kid": TEST_KID},
    )


@pytest.fixture
def client() -> Any:
    """Client on the full ASGI stack."""
    return create_app().test_client()


async def test_valid_token_is_accepted(client: Any) -> None:
    """Control: the baseline token used by every case below is accepted."""
    assert (await client.get(URL, headers=_hdr(_signed()))).status_code == 200


def _b64(raw: bytes) -> str:
    """URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _forged_hs256() -> str:
    """HS256 token MACed with the RSA public key bytes (classic alg-confusion attack).

    Built by hand because PyJWT itself refuses to sign HS256 with an asymmetric key.
    """
    pub = _generate_test_keypair()[1].public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": TEST_KID}).encode())
    body = _b64(json.dumps(mint_claims("u", "t1", "free")).encode())
    mac = hmac.new(pub, f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{_b64(mac)}"


def _alg_none() -> str:
    """Unsigned token declaring alg=none."""
    return jwt.encode(mint_claims("u", "t1", "free"), key=None, algorithm="none")  # type: ignore[arg-type]


def _tampered() -> str:
    """Valid token whose payload was swapped to another tenant, signature kept."""
    head, _, sig = _signed().split(".")
    other = _signed(tenant="t2").split(".")[1]
    return f"{head}.{other}.{sig}"


NOW = int(time.time())
BAD_TOKENS: dict[str, str] = {
    "alg_none": _alg_none(),
    "hs256_key_confusion": _forged_hs256(),
    "expired": _signed(exp=NOW - 3600, iat=NOW - 7200),
    "not_yet_valid": _signed(nbf=NOW + 3600),
    "wrong_iss": _signed(iss="https://evil.example"),
    "wrong_aud": _signed(aud="someone-else"),
    "missing_exp": _signed(exp=None),
    "missing_iat": _signed(iat=None),
    "missing_sub": _signed(sub=None),
    "missing_tenant": _signed(tenant=None),
    "empty_tenant": _signed(tenant="  "),
    "tampered_payload": _tampered(),
    "garbage": "not.a.jwt",
    "oversized": _signed(pad="x" * 9000),
}


@pytest.mark.parametrize("name", sorted(BAD_TOKENS))
async def test_bad_token_is_401(client: Any, name: str) -> None:
    """Every malformed/forged/expired token is rejected before Quart with 401."""
    r = await client.get(URL, headers=_hdr(BAD_TOKENS[name]))
    assert r.status_code == 401, name


@pytest.mark.parametrize("scheme", ["Basic dTpw", "bearer lowercase", "Bearer", ""])
async def test_non_bearer_authorization_is_401(client: Any, scheme: str) -> None:
    """Non-Bearer or empty Authorization values never authenticate."""
    r = await client.get(URL, headers={"Authorization": scheme})
    assert r.status_code == 401


def test_denominator_covers_the_documented_attack_classes() -> None:
    """The corpus must keep covering none/HS*/exp/nbf/iss/aud (guards against silent shrinkage)."""
    assert {
        "alg_none",
        "hs256_key_confusion",
        "expired",
        "not_yet_valid",
        "wrong_iss",
        "wrong_aud",
    } <= set(BAD_TOKENS)
    assert len(BAD_TOKENS) >= 14


async def test_tier_and_teams_survive_into_the_principal(client: Any) -> None:
    """The Nest tier claim reaches Principal (ext["tier"]) instead of being dropped."""
    from auth.rp import AsgiClaimsAdapter

    rp = AsgiClaimsAdapter(HardenedRP.from_env())
    claims = await rp.verify_token(
        _mint_token("u", "t1", "enterprise", ["*:read"], teams=["a", "b"])
    )
    assert claims["ext"] == {"tier": "enterprise"}
    assert claims["teams"] == ["a", "b"]
    assert claims["tenant"] == "t1"
    assert claims["iss"] == TEST_ISSUER
    assert claims["aud"] == [TEST_AUDIENCE]


def test_rp_refuses_non_rs_es_algorithms() -> None:
    """HS* / none can never be configured on the hardened RP."""
    from penguin_aaa.authn.oidc_rp import OIDCRPConfig

    cfg = OIDCRPConfig(
        issuer_url=TEST_ISSUER,
        client_id=TEST_AUDIENCE,
        client_secret="",
        redirect_url=TEST_ISSUER,
        algorithms=["RS256", "PS256"],
    )
    with pytest.raises(ValueError, match="only"):
        HardenedRP(cfg)


def test_from_env_requires_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    """No OIDC_ISSUER means no way to validate tokens: fail at startup, not per request."""
    monkeypatch.delenv("OIDC_ISSUER")
    with pytest.raises(RuntimeError, match="OIDC_ISSUER"):
        HardenedRP.from_env()
