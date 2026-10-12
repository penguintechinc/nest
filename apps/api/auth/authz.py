"""Principal, scope-guard decorator and tenant path guard for Quart handlers."""

from __future__ import annotations

import functools
import inspect
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast

import structlog
from auth.scopes import has_scope
from dto.problem import ProblemError
from obs import metrics
from quart import g, request

log = structlog.get_logger()

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


@dataclass(slots=True, frozen=True)
class Principal:
    """Authenticated caller identity derived from a validated token."""

    sub: str
    tenant: str
    scopes: tuple[str, ...]
    tier: str
    teams: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate tenant is a non-empty str and coerce scopes/teams to tuples."""
        if not isinstance(self.tenant, str) or not self.tenant:
            raise ValueError("Principal.tenant must be a non-empty string")
        for name in ("scopes", "teams"):
            value = getattr(self, name)
            if value is None or isinstance(value, str):
                raise ValueError(f"Principal.{name} must be an iterable of strings")
            try:
                coerced = tuple(value)
            except TypeError as exc:
                raise ValueError(
                    f"Principal.{name} must be an iterable of strings"
                ) from exc
            if not all(isinstance(item, str) for item in coerced):
                raise ValueError(f"Principal.{name} must contain only strings")
            object.__setattr__(self, name, coerced)


_TENANT_ARGS = frozenset({"tenant_id", "tid", "tenant"})
_RULE_ARG = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")
_TENANTS_SEGMENT = re.compile(r"/tenants/<(?:[^:<>]+:)?([^<>]+)>")


def _is_valid_scope(scope: str) -> bool:
    """Return True if scope is exactly "resource:action" with both parts non-empty."""
    parts = scope.split(":")
    return len(parts) == 2 and all(parts)


def current_principal() -> Principal:
    """Return the request's Principal or raise 401 if none was established."""
    principal = getattr(g, "principal", None)
    if not isinstance(principal, Principal):
        raise ProblemError(401, "nest.auth.unauthenticated", "authentication required")
    return principal


def require_scope(scope: str) -> Callable[[F], F]:
    """Decorate an async handler to require ``scope`` ("resource:action").

    Matches already-expanded scopes only; never role names. Sets
    ``__required_scope__`` on the handler so route audits can introspect it.
    """

    if not _is_valid_scope(scope):
        raise ValueError(
            f"malformed required scope: {scope!r} (want 'resource:action')"
        )

    def decorator(fn: F) -> F:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError("require_scope only wraps async handlers")

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            principal = current_principal()
            if not has_scope(principal.scopes, scope):
                metrics.auth_denied("scope_denied")
                log.info(
                    "scope_denied",
                    required=scope,
                    tenant=principal.tenant,
                    scope_count=len(principal.scopes),
                )
                raise ProblemError(403, "nest.auth.scope_denied", "insufficient scope")
            return await fn(*args, **kwargs)

        wrapper.__required_scope__ = scope  # type: ignore[attr-defined]  # dynamic marker attr
        return cast(F, wrapper)

    return decorator


async def tenant_path_guard() -> None:
    """before_request hook: enforce that the path tenant equals the token tenant.

    Fail-closed: a matched route that declares a tenant-looking arg under an
    unrecognized spelling (e.g. ``<tenantId>``, or whatever follows ``/tenants/``) is
    DENIED rather than silently skipped. Recognized spellings: tenant_id, tid, tenant.
    Values are compared as str so converters like ``<uuid:tenant_id>`` still match.
    Routes with no tenant arg at all (tenant comes from the token) are not gated here.
    """
    rule = request.url_rule.rule if request.url_rule is not None else ""
    declared = set(_RULE_ARG.findall(rule))
    suspicious = {m for m in _TENANTS_SEGMENT.findall(rule)} | {
        a for a in declared if "tenant" in a.lower()
    }
    unrecognized = suspicious - _TENANT_ARGS
    view_args = request.view_args or {}
    present = {k: v for k, v in view_args.items() if k in _TENANT_ARGS}
    if unrecognized:
        metrics.auth_denied("tenant_arg_unrecognized")
        log.warning("tenant_arg_unrecognized", rule=rule)
        raise ProblemError(403, "nest.auth.tenant_mismatch", "tenant mismatch")
    if not present:
        return
    principal = current_principal()
    for value in present.values():
        if str(value) != str(principal.tenant):
            metrics.auth_denied("tenant_mismatch")
            log.info("tenant_mismatch", tenant=principal.tenant)
            raise ProblemError(403, "nest.auth.tenant_mismatch", "tenant mismatch")
