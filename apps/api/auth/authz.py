"""Principal, scope-guard decorator and tenant path guard for Quart handlers."""

from __future__ import annotations

import functools
import inspect
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
    """before_request hook: reject when the path tenant_id differs from the token tenant."""
    view_args = request.view_args or {}
    path_tenant = view_args.get("tenant_id")
    if path_tenant is None:
        return
    principal = current_principal()
    if path_tenant != principal.tenant:
        metrics.auth_denied("tenant_mismatch")
        log.info("tenant_mismatch", tenant=principal.tenant)
        raise ProblemError(403, "nest.auth.tenant_mismatch", "tenant mismatch")
