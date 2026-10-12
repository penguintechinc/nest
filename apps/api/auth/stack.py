"""ASGI auth stack for the hub API: CORS preflight, penguin-aaa OIDC + tenant, claims bridge.

Order, outermost to innermost: per-request state isolation -> OTel (Task 7 hook, none yet) ->
RateLimit (Task 9 hook) -> CORS preflight -> public-path bypass | OIDCAuthMiddleware ->
TenantMiddleware -> Quart.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, cast

from adapters.limiter import RateLimiter
from auth.authz import Principal
from auth.rp import IDP_OUTAGE
from dto.problem import ProblemError
from penguin_aaa.middleware.asgi import OIDCAuthMiddleware
from penguin_aaa.middleware.tenant import TenantMiddleware
from quart import Quart

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

PUBLIC_PATHS: frozenset[str] = frozenset(
    {"/health", "/ready", "/metrics", "/saml/metadata", "/saml/acs"}
)

CORS_ENV = "NEST_CORS_ORIGINS"
_CORS_METHODS = b"GET, POST, PUT, PATCH, DELETE, OPTIONS"
_CORS_HEADERS = b"Authorization, Content-Type, X-Request-ID"


def cors_origins_from_env() -> frozenset[str]:
    """Parse NEST_CORS_ORIGINS (comma-separated); default none. A wildcard is rejected."""
    origins = frozenset(
        o.strip() for o in os.environ.get(CORS_ENV, "").split(",") if o.strip()
    )
    if "*" in origins:
        raise ValueError(f"{CORS_ENV} must list explicit origins, never '*'")
    return origins


class RequestStateIsolation:
    """Give every request its own ``scope["state"]`` dict before anything writes claims.

    ASGI servers (hypercorn) copy lifespan ``state`` per CONNECTION, so HTTP/2 streams that
    multiplex on one connection would otherwise share one dict and a claims write for tenant B
    could be observed by tenant A's request. This must be the OUTERMOST layer.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap ``app``."""
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Replace the shared state with a private shallow copy for http/websocket scopes."""
        if scope["type"] in ("http", "websocket"):
            scope = {**scope, "state": dict(scope.get("state") or {})}
        await self._app(scope, receive, send)


_OUTAGE_BODY = b'{"error": "Identity provider unavailable"}'


class IdpOutageAwareOIDC(OIDCAuthMiddleware):
    """OIDCAuthMiddleware that answers 503 (+Retry-After) when the IdP is down, not 401.

    The stock middleware turns every verification exception into 401, which would tell clients
    their (valid) credentials are bad during an IdP outage. ``AsgiClaimsAdapter`` flags the
    outage via a context variable; this layer rewrites that one 401 response.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Delegate, rewriting the middleware's own 401 to 503 when the outage flag is set."""
        IDP_OUTAGE.set(False)
        rewriting = False

        async def send_mapped(message: dict[str, Any]) -> None:
            nonlocal rewriting
            if (
                message["type"] == "http.response.start"
                and message.get("status") == 401
                and IDP_OUTAGE.get()
            ):
                rewriting = True
                message = {
                    "type": "http.response.start",
                    "status": 503,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(_OUTAGE_BODY)).encode()),
                        (b"retry-after", b"5"),
                    ],
                }
            elif rewriting and message["type"] == "http.response.body":
                message = {"type": "http.response.body", "body": _OUTAGE_BODY}
            await send(message)

        await super().__call__(scope, receive, send_mapped)


def _header(scope: Scope, name: bytes) -> bytes:
    """Return the first request header value matching ``name`` (lowercase), or b""."""
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return bytes(value)
    return b""


class CorsMiddleware:
    """Answer CORS preflights before auth and tag responses for allow-listed origins.

    A preflight (OPTIONS + Origin + Access-Control-Request-Method) never carries credentials,
    so it must not require a token. With no allowed origins it still answers 204 but grants
    nothing, so browsers block the real request.
    """

    def __init__(self, app: ASGIApp, allowed_origins: frozenset[str]) -> None:
        """Wrap ``app``; ``allowed_origins`` is an exact-match allow-list."""
        self._app = app
        self._allowed = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Short-circuit preflights; otherwise add CORS headers to allowed-origin responses."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        origin = _header(scope, b"origin").decode("latin-1")
        allowed = bool(origin) and origin in self._allowed
        preflight = (
            scope.get("method") == "OPTIONS"
            and bool(origin)
            and bool(_header(scope, b"access-control-request-method"))
        )
        if preflight:
            headers: list[tuple[bytes, bytes]] = [(b"content-length", b"0")]
            if allowed:
                headers += [
                    (b"access-control-allow-origin", origin.encode("latin-1")),
                    (b"access-control-allow-methods", _CORS_METHODS),
                    (b"access-control-allow-headers", _CORS_HEADERS),
                    (b"access-control-max-age", b"600"),
                    (b"vary", b"Origin"),
                ]
            await send(
                {"type": "http.response.start", "status": 204, "headers": headers}
            )
            await send({"type": "http.response.body", "body": b""})
            return
        if not allowed:
            await self._app(scope, receive, send)
            return

        async def send_with_cors(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = [
                    *message.get("headers", []),
                    (b"access-control-allow-origin", origin.encode("latin-1")),
                    (b"vary", b"Origin"),
                ]
            await send(message)

        await self._app(scope, receive, send_with_cors)


class PublicPathBypass:
    """Route exact public paths straight to the app, everything else through the auth chain."""

    def __init__(
        self, public_app: ASGIApp, authed_app: ASGIApp, public: frozenset[str]
    ) -> None:
        """Hold both branches and the exact-match public path set."""
        self._public_app = public_app
        self._authed_app = authed_app
        self._public = public

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Dispatch on the exact request path; non-http scopes (lifespan) pass to the app."""
        if scope["type"] == "http" and scope.get("path", "") in self._public:
            await self._public_app(scope, receive, send)
        else:
            await self._authed_app(scope, receive, send)


def principal_from_claims(claims: Any) -> Principal:
    """Build a Principal from the validated claims mapping; fail closed with a 401 Problem."""
    if not isinstance(claims, Mapping):
        raise ProblemError(401, "nest.auth.invalid_claims", "invalid token claims")
    ext = claims.get("ext")
    tier = ext.get("tier") if isinstance(ext, Mapping) else None
    try:
        return Principal(
            sub=str(claims["sub"]),
            tenant=claims["tenant"],
            scopes=claims.get("scope") or (),
            tier=tier if isinstance(tier, str) and tier else "free",
            teams=claims.get("teams") or (),
        )
    except (KeyError, ValueError) as exc:
        raise ProblemError(
            401, "nest.auth.invalid_claims", "invalid token claims"
        ) from exc


def build_asgi_stack(
    app: Quart,
    *,
    rp: Any,
    limiter: RateLimiter | None,
    public_paths: frozenset[str],
) -> None:
    """Wrap ``app.asgi_app`` in the auth stack. ``rp.verify_token`` must return a mapping."""
    if limiter is not None:
        # Fail loud: the rate-limit layer lands in Task 9; never silently ignore a limiter.
        raise NotImplementedError("rate limiting ASGI layer is implemented in Task 9")
    quart_app = cast(ASGIApp, app.asgi_app)
    authed = IdpOutageAwareOIDC(
        TenantMiddleware(quart_app, required=True), rp, public_paths=set(public_paths)
    )
    stack: ASGIApp = PublicPathBypass(quart_app, authed, public_paths)
    stack = CorsMiddleware(stack, cors_origins_from_env())
    stack = RequestStateIsolation(stack)
    app.asgi_app = stack  # type: ignore[method-assign,assignment]  # documented Quart middleware hook
