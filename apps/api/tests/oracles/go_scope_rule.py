"""Oracle re-implementing services/gateway/internal/middleware/scope.go derivation."""

from __future__ import annotations

_ACTIONS = {
    "GET": "read",
    "HEAD": "read",
    "OPTIONS": "read",
    "POST": "write",
    "PUT": "write",
    "PATCH": "write",
    "DELETE": "admin",
}


def derive(method: str, path: str) -> str | None:
    """Return the "resource:action" scope Go would require, or None (deny) if undetermined."""
    action = _ACTIONS.get(method)
    if action is None:
        return None
    rest = path.removeprefix("/api/v1/")
    parts = rest.split("/")
    if parts[0] == "tenants" and len(parts) > 2:
        resource = parts[2]
    else:
        resource = parts[0]
    if not resource:
        return None
    return f"{resource}:{action}"
