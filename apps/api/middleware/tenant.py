"""Request-context accessors for the authenticated Principal.

Authentication, tenant enforcement and scope checks live in ``auth/`` and the ASGI stack
(``auth/stack.py``); these shims only expose what that stack placed on ``g.principal`` so the
existing handlers keep a stable ``get_tenant()`` / ``get_claims()`` surface.
"""

from __future__ import annotations

from auth.authz import Principal
from quart import g

# Backwards-compatible name for handler type hints; the shape is a Principal.
Claims = Principal


def get_tenant() -> str:
    """Return the validated tenant from the token (never from the request), or "" if none."""
    principal = getattr(g, "principal", None)
    return principal.tenant if isinstance(principal, Principal) else ""


def get_claims() -> Principal | None:
    """Return the request's Principal, or None for unauthenticated (public) requests."""
    principal = getattr(g, "principal", None)
    return principal if isinstance(principal, Principal) else None
