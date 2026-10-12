"""Route audit: every route is scope-guarded and every tenant-scoped route hits the tenant guard."""

from __future__ import annotations

import re
from typing import Any

import pytest
from app import create_app
from auth.authz import require_scope, tenant_path_guard
from auth.stack import PUBLIC_PATHS
from quart import Quart

from tests.tokens import _mint_token

_ARG = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")
_SKIP_METHODS = {"HEAD", "OPTIONS"}


def unprotected_routes(app: Quart) -> list[str]:
    """Return non-public routes whose view function lacks the ``@require_scope`` marker."""
    bad: list[str] = []
    for rule in app.url_map.iter_rules():
        if rule.rule in PUBLIC_PATHS:
            continue
        view = app.view_functions[rule.endpoint]
        if not getattr(view, "__required_scope__", None):
            bad.append(f"{rule.rule} ({rule.endpoint})")
    return bad


def _concrete(rule: str, tenant: str) -> str:
    """Fill a rule: tenant_id -> ``tenant``, every other arg -> ``x``."""
    return _ARG.sub(lambda m: tenant if m.group(1) == "tenant_id" else "x", rule)


def tenant_routes(app: Quart) -> list[tuple[str, str]]:
    """Return (method, rule) for every tenant-scoped route (any arg containing 'tenant')."""
    out: list[tuple[str, str]] = []
    for rule in app.url_map.iter_rules():
        if any("tenant" in a.lower() for a in _ARG.findall(rule.rule)):
            out += [
                (m, rule.rule) for m in sorted((rule.methods or set()) - _SKIP_METHODS)
            ]
    return out


def test_every_non_public_route_declares_a_scope() -> None:
    """No handler may ship without the @require_scope marker (denominator asserted)."""
    app = create_app()
    rules = list(app.url_map.iter_rules())
    assert len(rules) >= 25, f"route audit examined only {len(rules)} rules"
    assert unprotected_routes(app) == []


def test_audit_detects_an_unmarked_route() -> None:
    """The audit must be able to fail: an unmarked route and a bare static route are flagged."""
    app = Quart(__name__, static_folder=None)

    @app.route("/api/v1/tenants/<tenant_id>/oops")
    async def oops(tenant_id: str) -> str:
        return "no scope"

    @app.route("/api/v1/ok")
    @require_scope("ok:read")
    async def fine() -> str:
        return "ok"

    assert unprotected_routes(app) == ["/api/v1/tenants/<tenant_id>/oops (oops)"]
    assert "static" not in {r.endpoint for r in create_app().url_map.iter_rules()}


def test_tenant_guard_is_registered_right_after_the_claims_bridge() -> None:
    """The guard must run on every request, immediately after the hook that sets g.principal."""
    funcs = create_app().before_request_funcs[None]
    assert funcs[1] is tenant_path_guard
    assert funcs[0].__name__ == "bridge_request"
    assert len(funcs) == 2


def test_every_tenant_route_uses_the_recognized_arg_name() -> None:
    """All tenant routes spell the arg tenant_id, so the guard can never skip one."""
    app = create_app()
    pairs = tenant_routes(app)
    assert (
        len(pairs) >= 20
    ), f"examined only {len(pairs)} tenant-scoped (method, route) pairs"
    for _method, rule in pairs:
        assert "tenant_id" in _ARG.findall(rule), rule
        assert [a for a in _ARG.findall(rule) if "tenant" in a.lower()] == [
            "tenant_id"
        ], rule


async def test_every_tenant_route_triggers_tenant_path_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real request per (method, tenant route): a foreign path tenant is stopped by the guard.

    ``nest.auth.tenant_mismatch`` is only ever emitted by tenant_path_guard, and a spy proves the
    registered hook itself ran (once per request) with the same call count as requests sent.
    """
    import app as app_module

    calls: list[str] = []

    async def spy() -> None:
        calls.append("guard")
        await tenant_path_guard()

    monkeypatch.setattr(app_module, "tenant_path_guard", spy)
    app = create_app()
    client: Any = app.test_client()
    tok = _mint_token("u", "t1", "free", ["nest:*:admin"])
    headers = {"Authorization": f"Bearer {tok}"}
    pairs = tenant_routes(app)
    assert len(pairs) >= 20

    for method, rule in pairs:
        before = len(calls)
        r = await client.open(_concrete(rule, "other"), method=method, headers=headers)
        body: Any = await r.get_json()
        assert r.status_code == 403, (method, rule, r.status_code)
        assert body["code"] == "nest.auth.tenant_mismatch", (method, rule, body)
        assert len(calls) == before + 1, (method, rule)

        # Control: the same route with the token's own tenant is NOT stopped by the guard.
        ok = await client.open(_concrete(rule, "t1"), method=method, headers=headers)
        ok_body: Any = await ok.get_json(silent=True)
        assert not (
            isinstance(ok_body, dict)
            and ok_body.get("code") == "nest.auth.tenant_mismatch"
        )
