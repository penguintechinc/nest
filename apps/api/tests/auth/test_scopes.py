"""Scope matcher tests."""

import pytest
from auth.scopes import has_scope


@pytest.mark.parametrize(
    "granted,required,ok",
    [
        (["*:read"], "databases:read", True),
        (["*:read"], "databases:write", False),
        (["databases:admin"], "databases:write", True),
        (["databases:admin"], "engines:read", False),
        (["*:admin"], "anything:delete", False),
        (["*:delete"], "anything:delete", True),
        (["analytics:write"], "databases:write", False),
        (["a:b:c"], "a:b", False),
        (["nest:*:admin"], "dataresources:write", True),
        (["nest:dataresource:delete"], "dataresources:admin", True),
        (["nest:dataresource:read"], "dataresources:write", False),
        ([], "x:read", False),
        ([""], "x:read", False),
        (["x:read"], "malformed", False),
    ],
)
def test_has_scope(granted: list[str], required: str, ok: bool) -> None:
    """Matcher follows Go semantics plus legacy aliases; admin never implies delete."""
    assert has_scope(granted, required) is ok
