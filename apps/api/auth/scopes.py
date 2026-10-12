"""OIDC scope matcher ported from the Go gateway scope rule.

Scopes arrive ALREADY EXPANDED: role bundles expand at token issuance, never here.
This module matches scopes only and never inspects role names.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

LEGACY_SCOPE_ALIASES: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "dataresources:read": frozenset({"nest:dataresource:read"}),
        "dataresources:write": frozenset({"nest:dataresource:write"}),
        "dataresources:admin": frozenset({"nest:dataresource:delete"}),
    }
)

_LEGACY_SUPER_GRANT = "nest:*:admin"
# Actions the literal "admin" action covers. "delete" is deliberately absent: DELETE
# maps to the "admin" action, and "admin" never implies a distinct "delete" scope.
_ADMIN_COVERS = frozenset({"read", "write", "admin"})


def _action_matches(granted: str, required: str) -> bool:
    """Return True when a granted action satisfies the required action."""
    return granted == required or (granted == "admin" and required in _ADMIN_COVERS)


def has_scope(granted: Iterable[str], required: str) -> bool:
    """Return True if any granted scope satisfies ``required`` ("resource:action").

    Grant "r:a" satisfies required "R:A" iff the action matches (a == A, or a is
    "admin" covering read/write/admin) and the resource matches (r == R or r == "*").
    Grants not of the form "x:y" (exactly one colon) are ignored, except the legacy
    super-grant "nest:*:admin". Legacy aliases map old names to required scopes.
    """
    req_parts = required.split(":")
    if len(req_parts) != 2 or not all(req_parts):
        return False
    req_res, req_act = req_parts
    legacy = LEGACY_SCOPE_ALIASES.get(required, frozenset())
    for scope in granted:
        if scope == _LEGACY_SUPER_GRANT or scope in legacy:
            return True
        parts = scope.split(":")
        if len(parts) != 2:
            continue
        res, act = parts
        if not res or not act:
            continue
        if _action_matches(act, req_act) and res in (req_res, "*"):
            return True
    return False
