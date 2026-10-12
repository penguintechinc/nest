"""Principal / require_scope / tenant_path_guard tests."""

import uuid

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


def _guard_app() -> Quart:
    app = Quart(__name__)

    @app.route("/t/<tenant_id>/x")
    async def r1(tenant_id: str) -> str:
        return ""

    @app.route("/u/<tid>/x")
    async def r2(tid: str) -> str:
        return ""

    @app.route("/v/<tenantId>/x")
    async def r3(tenantId: str) -> str:  # noqa: N803
        return ""

    @app.route("/w/<uuid:tenant_id>/x")
    async def r4(tenant_id: uuid.UUID) -> str:
        return ""

    @app.route("/tenants/<org>/x")
    async def r5(org: str) -> str:
        return ""

    @app.route("/health")
    async def r6() -> str:
        return ""

    return app


@pytest.mark.parametrize("path", ["/t/t1/x", "/u/t1/x"])
async def test_guard_allows_matching_tenant(path: str) -> None:
    async with _guard_app().test_request_context(path):
        g.principal = _p((), "t1")
        await tenant_path_guard()


@pytest.mark.parametrize("path", ["/t/t2/x", "/u/t2/x"])
async def test_guard_denies_mismatch(path: str) -> None:
    async with _guard_app().test_request_context(path):
        g.principal = _p((), "t1")
        with pytest.raises(ProblemError) as ei:
            await tenant_path_guard()
    assert (ei.value.status, ei.value.code) == (403, "nest.auth.tenant_mismatch")


@pytest.mark.parametrize("path", ["/v/t1/x", "/tenants/t1/x"])
async def test_guard_fails_closed_on_unrecognized_tenant_arg(path: str) -> None:
    async with _guard_app().test_request_context(path):
        g.principal = _p((), "t1")
        with pytest.raises(ProblemError) as ei:
            await tenant_path_guard()
    assert ei.value.status == 403


async def test_guard_uuid_converter_normalized() -> None:
    tid = uuid.uuid4()
    async with _guard_app().test_request_context(f"/w/{tid}/x"):
        g.principal = _p((), str(tid))
        await tenant_path_guard()
    async with _guard_app().test_request_context(f"/w/{uuid.uuid4()}/x"):
        g.principal = _p((), str(tid))
        with pytest.raises(ProblemError) as ei:
            await tenant_path_guard()
    assert ei.value.status == 403


async def test_guard_absent_principal_with_tenant_path_is_401() -> None:
    async with _guard_app().test_request_context("/t/t1/x"):
        with pytest.raises(ProblemError) as ei:
            await tenant_path_guard()
    assert (ei.value.status, ei.value.code) == (401, "nest.auth.unauthenticated")


async def test_guard_skips_route_without_tenant_arg() -> None:
    async with _guard_app().test_request_context("/health"):
        await tenant_path_guard()


async def test_admin_scope_does_not_grant_delete() -> None:
    @require_scope("x:delete")
    async def handler() -> str:
        return "ok"

    async with Quart(__name__).test_request_context("/"):
        g.principal = _p(("admin:admin", "*:admin"))
        with pytest.raises(ProblemError) as ei:
            await handler()
    assert ei.value.code == "nest.auth.scope_denied"


async def test_empty_scope_principal_denied() -> None:
    @require_scope("x:read")
    async def handler() -> str:
        return "ok"

    async with Quart(__name__).test_request_context("/"):
        g.principal = _p(())
        with pytest.raises(ProblemError) as ei:
            await handler()
    assert (ei.value.status, ei.value.code) == (403, "nest.auth.scope_denied")


@pytest.mark.parametrize("bad", ["", "x", "a:b:c", ":read", "x:"])
def test_require_scope_rejects_malformed_scope(bad: str) -> None:
    with pytest.raises(ValueError):
        require_scope(bad)


def test_principal_validation() -> None:
    with pytest.raises(ValueError):
        Principal(sub="u", tenant="", scopes=(), tier="free", teams=())
    with pytest.raises(ValueError):
        Principal(sub="u", tenant="t", scopes=None, tier="free", teams=())  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Principal(sub="u", tenant="t", scopes="x:read", tier="free", teams=())  # type: ignore[arg-type]
    p = Principal(sub="u", tenant="t", scopes=["x:read"], tier="free", teams=[])  # type: ignore[arg-type]
    assert p.scopes == ("x:read",)
    assert p.teams == ()
