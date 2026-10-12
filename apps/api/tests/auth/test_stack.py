"""Auth stack tests driven through the real ASGI path (Quart.__call__ -> app.asgi_app)."""

from __future__ import annotations

from typing import Any

import pytest
from app import create_app
from auth.authz import current_principal, require_scope
from auth.stack import CORS_ENV, PUBLIC_PATHS
from quart import Quart, request

from tests.tokens import _mint_token

DR = "/api/v1/tenants/{}/data-resources"


@pytest.fixture
async def client() -> Any:
    """Client on the full ASGI stack (no `async with`: see conftest `client`)."""
    return create_app().test_client()


def _bearer(token: str, **extra: str) -> dict[str, str]:
    """Authorization header (plus extras) for a minted token."""
    return {"Authorization": f"Bearer {token}", **extra}


async def test_asgi_stack_is_installed_on_the_app() -> None:
    """Quart.__call__ must route through the wrapped asgi_app, or none of this is tested."""
    app = create_app()
    assert type(app.asgi_app).__name__ == "CorsMiddleware"
    assert app.asgi_app is not Quart.asgi_app.__get__(app)


async def test_missing_bearer_is_401(client: Any) -> None:
    """No token on an authenticated route is rejected before Quart."""
    r = await client.get(DR.format("t1"))
    assert r.status_code == 401


async def test_public_paths_need_no_token(client: Any) -> None:
    """Health/readiness/metrics/SAML metadata are reachable anonymously."""
    for p in ("/health", "/ready", "/metrics", "/saml/metadata"):
        assert (await client.get(p)).status_code != 401, p


def test_public_paths_are_exactly_the_documented_set() -> None:
    """Guard against silently widening the anonymous surface."""
    assert PUBLIC_PATHS == frozenset(
        {"/health", "/ready", "/metrics", "/saml/metadata", "/saml/acs"}
    )


@pytest.mark.parametrize(
    "path", ["/health/", "/health/x", "/HEALTH", "/metrics/../api/v1/catalog"]
)
async def test_public_path_lookalikes_still_need_auth(client: Any, path: str) -> None:
    """Only exact public paths bypass auth; lookalikes are authenticated (401)."""
    assert (await client.get(path)).status_code == 401


@pytest.mark.parametrize(
    "path_tenant", ["T1", "t1/", "%74%32", "t2", "..", "t1%2f..%2ft2"]
)
async def test_tenant_lookalikes_never_cross_tenant(
    client: Any, path_tenant: str
) -> None:
    """Any path tenant that is not exactly the token tenant is denied (never 200).

    "t1/" is the one benign case: werkzeug merges the double slash and 308-redirects to the
    canonical same-tenant URL (no data served; the follow-up is re-guarded).
    """
    tok = _mint_token("u", "t1", "free", ["*:admin"])
    r = await client.get(DR.format(path_tenant), headers=_bearer(tok))
    assert r.status_code in (308, 403, 404)
    if r.status_code == 308:
        assert r.headers["location"].endswith("/api/v1/tenants/t1/data-resources")


async def test_percent_encoded_same_tenant_is_same_tenant(client: Any) -> None:
    """%74%31 decodes to t1: that is NOT a mismatch (contrast with %74%32 -> t2 above)."""
    tok = _mint_token("u", "t1", "free", ["*:read"])
    r = await client.get(DR.format("%74%31"), headers=_bearer(tok))
    assert r.status_code == 200


async def test_same_tenant_ok_and_tenant_taken_from_jwt(client: Any) -> None:
    """A client-supplied X-Tenant header can never change the tenant."""
    tok = _mint_token("u", "t1", "free", ["*:read"])
    r = await client.get(DR.format("t1"), headers=_bearer(tok, **{"X-Tenant": "t2"}))
    assert r.status_code == 200


async def test_options_preflight_needs_no_token(client: Any) -> None:
    """A CORS preflight is answered before auth."""
    r = await client.options(
        DR.format("t1"),
        headers={"Origin": "https://x", "Access-Control-Request-Method": "GET"},
    )
    assert r.status_code in (200, 204)
    assert "access-control-allow-origin" not in r.headers  # no origins configured


async def test_plain_options_without_preflight_headers_needs_auth(client: Any) -> None:
    """Only a real preflight bypasses auth; a bare OPTIONS is authenticated."""
    assert (await client.options(DR.format("t1"))).status_code == 401


async def test_unknown_method_is_405_not_500(client: Any) -> None:
    """An unsupported method on a known route is 405, never a 500."""
    tok = _mint_token("u", "t1", "free", ["*:admin"])
    r = await client.open(DR.format("t1"), method="TRACE", headers=_bearer(tok))
    assert r.status_code == 405


async def test_cors_allowed_origin_gets_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An allow-listed origin gets preflight grants and response tagging."""
    monkeypatch.setenv(CORS_ENV, "https://ui.example, https://other.example")
    c = create_app().test_client()
    pre = await c.options(
        DR.format("t1"),
        headers={
            "Origin": "https://ui.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert pre.status_code == 204
    assert pre.headers["access-control-allow-origin"] == "https://ui.example"
    live = await c.get("/health", headers={"Origin": "https://ui.example"})
    assert live.headers["access-control-allow-origin"] == "https://ui.example"
    denied = await c.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in denied.headers


def test_cors_wildcard_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """NEST_CORS_ORIGINS=* is a configuration error, not a silent allow-all."""
    monkeypatch.setenv(CORS_ENV, "*")
    with pytest.raises(ValueError, match="never"):
        create_app()


def test_limiter_fails_loud_until_task_9() -> None:
    """A supplied limiter must not be silently ignored."""
    with pytest.raises(NotImplementedError):
        create_app(limiter=object())  # type: ignore[arg-type]


async def test_scope_denied_is_403_problem_not_500(client: Any) -> None:
    """ProblemError from require_scope renders as a 403 Problem body."""
    tok = _mint_token("u", "t1", "free", ["*:read"])
    r = await client.post(
        DR.format("t1"), json={}, headers=_bearer(tok, **{"X-Request-ID": "rid-1"})
    )
    assert r.status_code == 403
    body = await r.get_json()
    assert body["code"] == "nest.auth.scope_denied"
    assert body["requestId"] == "rid-1"
    assert body["docsUrl"].endswith("/nest.auth.scope_denied")
    assert set(body) == {"code", "message", "requestId", "docsUrl"}


async def test_tenant_mismatch_is_403_problem_not_500(client: Any) -> None:
    """ProblemError from tenant_path_guard renders as a 403 Problem body."""
    tok = _mint_token("u", "t1", "free", ["*:admin"])
    r = await client.get(DR.format("t2"), headers=_bearer(tok))
    assert r.status_code == 403
    assert (await r.get_json())["code"] == "nest.auth.tenant_mismatch"


async def test_missing_principal_on_authed_route_is_401_problem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the ASGI layer is bypassed (no claims), require_scope fails closed with a 401 Problem."""
    monkeypatch.setattr("app.build_asgi_stack", lambda *a, **k: None)
    app = create_app()
    r = await app.test_client().get("/api/v1/catalog")
    assert r.status_code == 401
    assert (await r.get_json())["code"] == "nest.auth.unauthenticated"


def _probe_app(calls: list[dict[str, Any]]) -> Quart:
    """create_app() plus a probe route registered through REAL routing."""
    app = create_app()

    @app.route("/api/v1/tenants/<tenant_id>/probe", methods=["GET"])
    @require_scope("probe:read")
    async def probe(tenant_id: str) -> dict[str, Any]:
        p = current_principal()
        calls.append(
            {
                "view_args": dict(request.view_args or {}),
                "tenant": p.tenant,
                "tier": p.tier,
                "teams": p.teams,
            }
        )
        return {"tenant": p.tenant}

    @app.route("/api/v1/tenants/<tenantId>/camel", methods=["GET"])
    @require_scope("probe:read")
    async def camel(tenantId: str) -> dict[str, Any]:  # noqa: N803
        calls.append({"camel": tenantId})
        return {}

    return app


async def test_real_routing_populates_view_args_and_guard_runs_before_handler() -> None:
    """Through a real request: view_args is populated, the guard blocks a mismatch, handler never runs."""
    calls: list[dict[str, Any]] = []
    c = _probe_app(calls).test_client()
    tok = _mint_token("u", "t1", "pro", ["probe:read"], teams=["core"])

    ok = await c.get("/api/v1/tenants/t1/probe", headers=_bearer(tok))
    assert ok.status_code == 200
    assert calls == [
        {
            "view_args": {"tenant_id": "t1"},
            "tenant": "t1",
            "tier": "pro",
            "teams": ("core",),
        }
    ]

    calls.clear()
    bad = await c.get("/api/v1/tenants/t2/probe", headers=_bearer(tok))
    assert bad.status_code == 403
    assert (await bad.get_json())["code"] == "nest.auth.tenant_mismatch"
    assert calls == []  # guard fired before the handler


async def test_real_routing_unrecognized_tenant_arg_spelling_is_denied() -> None:
    """A route using <tenantId> is denied (fail-closed) even for the matching tenant."""
    calls: list[dict[str, Any]] = []
    c = _probe_app(calls).test_client()
    tok = _mint_token("u", "t1", "pro", ["probe:read"])
    r = await c.get("/api/v1/tenants/t1/camel", headers=_bearer(tok))
    assert r.status_code == 403
    assert calls == []
