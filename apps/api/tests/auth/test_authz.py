"""Principal / require_scope / tenant_path_guard tests."""

import pytest
from auth.authz import Principal, current_principal, require_scope, tenant_path_guard
from dto.problem import ProblemError
from quart import Quart, g


def _p(scopes: tuple[str, ...], tenant: str = "t1") -> Principal:
    return Principal(sub="u", tenant=tenant, scopes=scopes, tier="free", teams=())


def test_requires_async() -> None:
    def sync_fn() -> None: ...

    with pytest.raises(TypeError):
        require_scope("x:read")(sync_fn)  # type: ignore[type-var]


async def test_current_principal_absent() -> None:
    app = Quart(__name__)
    async with app.test_request_context("/"):
        with pytest.raises(ProblemError) as ei:
            current_principal()
    assert (ei.value.status, ei.value.code) == (401, "nest.auth.unauthenticated")


async def test_require_scope_allow_deny_and_marker() -> None:
    app = Quart(__name__)

    @require_scope("databases:write")
    async def handler() -> str:
        return "ok"

    assert handler.__required_scope__ == "databases:write"  # type: ignore[attr-defined]
    async with app.test_request_context("/"):
        g.principal = _p(("*:write",))
        assert await handler() == "ok"
        g.principal = _p(("*:read",))
        with pytest.raises(ProblemError) as ei:
            await handler()
    assert (ei.value.status, ei.value.code) == (403, "nest.auth.scope_denied")


async def test_require_scope_unauthenticated() -> None:
    app = Quart(__name__)

    @require_scope("x:read")
    async def handler() -> str:
        return "ok"

    async with app.test_request_context("/"):
        with pytest.raises(ProblemError) as ei:
            await handler()
    assert ei.value.status == 401


async def test_tenant_path_guard() -> None:
    app = Quart(__name__)

    @app.route("/t/<tenant_id>/x")
    async def route(tenant_id: str) -> str:
        return ""

    async with app.test_request_context("/t/t1/x"):
        from quart import request

        request.url_rule  # noqa: B018
        request.view_args = {"tenant_id": "t1"}  # type: ignore[misc]
        g.principal = _p((), "t1")
        await tenant_path_guard()
        request.view_args = {"tenant_id": "t2"}  # type: ignore[misc]
        with pytest.raises(ProblemError) as ei:
            await tenant_path_guard()
        assert (ei.value.status, ei.value.code) == (403, "nest.auth.tenant_mismatch")
        request.view_args = {}  # type: ignore[misc]
        await tenant_path_guard()
