"""Per-request ASGI state: no claim bleed between requests sharing one connection."""

from __future__ import annotations

import asyncio
from typing import Any

from app import create_app
from auth.authz import current_principal, require_scope
from auth.rp import AsgiClaimsAdapter, HardenedRP
from quart import Quart

from tests.tokens import _mint_token


class _BarrierRP:
    """Verify for real, then rendezvous so both requests write claims at the same moment."""

    def __init__(self, inner: AsgiClaimsAdapter, parties: int) -> None:
        self._inner = inner
        self._barrier = asyncio.Barrier(parties)

    async def verify_token(self, raw_token: str) -> dict[str, Any]:
        claims = await self._inner.verify_token(raw_token)
        await self._barrier.wait()
        return claims


def _scope(path: str, token: str, state: dict[str, Any]) -> dict[str, Any]:
    """Hand-built HTTP ASGI scope; ``state`` is the connection-shared dict."""
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "2",
        "method": "GET",
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"hub.test"),
            (b"authorization", f"Bearer {token}".encode()),
        ],
        "client": ("203.0.113.9", 4242),
        "server": ("hub.test", 443),
        "extensions": {},
        "state": state,
    }


async def _call(app: Quart, scope: dict[str, Any]) -> tuple[int, bytes]:
    """Drive ``app`` over raw ASGI; ``receive`` yields so other requests interleave."""
    events: list[dict[str, Any]] = [
        {"type": "http.request", "body": b"", "more_body": False}
    ]

    async def receive() -> dict[str, Any]:
        await asyncio.sleep(
            0
        )  # a real network read suspends; let the sibling stream run
        return events.pop(0) if events else {"type": "http.disconnect"}

    status = 0
    body = bytearray()

    async def send(message: dict[str, Any]) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
        elif message["type"] == "http.response.body":
            body.extend(message.get("body", b""))

    asgi: Any = app  # typed against hypercorn's TypedDicts; we speak plain dicts
    await asgi(scope, receive, send)
    return status, bytes(body)


def _app(parties: int) -> Quart:
    """App with a probe route and a rendezvous RP so the claims race is forced."""
    rp = _BarrierRP(AsgiClaimsAdapter(HardenedRP.from_env()), parties)
    app = create_app(rp=rp)

    @app.route("/api/v1/tenants/<tenant_id>/whoami", methods=["GET"])
    @require_scope("probe:read")
    async def whoami(tenant_id: str) -> dict[str, str]:
        return {"tenant": current_principal().tenant, "sub": current_principal().sub}

    return app


async def test_interleaved_tenants_on_one_connection_do_not_bleed_claims() -> None:
    """Two streams, SAME shared state dict, different tenants: each sees only its own claims."""
    app = _app(parties=2)
    shared: dict[str, Any] = {}
    tok_a = _mint_token("alice", "t1", "free", ["probe:read"])
    tok_b = _mint_token("bob", "t2", "free", ["probe:read"])

    (st_a, body_a), (st_b, body_b) = await asyncio.gather(
        _call(app, _scope("/api/v1/tenants/t1/whoami", tok_a, shared)),
        _call(app, _scope("/api/v1/tenants/t2/whoami", tok_b, shared)),
    )

    assert (st_a, st_b) == (200, 200), (body_a, body_b)
    assert b'"alice"' in body_a and b'"t1"' in body_a
    assert b'"bob"' in body_b and b'"t2"' in body_b
    assert shared == {}  # the connection-level dict was never written


async def test_many_interleaved_requests_never_cross_tenants() -> None:
    """Stress: 10 tenants multiplexed on one shared state, every response is its own tenant."""
    n = 10
    app = _app(parties=n)
    shared: dict[str, Any] = {}
    calls = [
        _call(
            app,
            _scope(
                f"/api/v1/tenants/t{i}/whoami",
                _mint_token(f"u{i}", f"t{i}", "free", ["probe:read"]),
                shared,
            ),
        )
        for i in range(n)
    ]
    results = await asyncio.gather(*calls)
    assert len(results) == n
    for i, (status, body) in enumerate(results):
        assert status == 200, body
        assert f'"t{i}"'.encode() in body and f'"u{i}"'.encode() in body
