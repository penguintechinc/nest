"""Oracle self-test so the Go-rule reimplementation cannot silently rot."""

import pytest

from tests.oracles.go_scope_rule import derive


@pytest.mark.parametrize(
    "m,p,exp",
    [
        ("GET", "/api/v1/tenants/t1/databases", "databases:read"),
        ("DELETE", "/api/v1/tenants/t1/databases/x", "databases:admin"),
        ("POST", "/api/v1/query", "query:write"),
        ("PUT", "/api/v1/objects/r/b/k", "objects:write"),
        ("TRACE", "/api/v1/query", None),
    ],
)
def test_derive(m: str, p: str, exp: str | None) -> None:
    """Derivation mirrors scope.go."""
    assert derive(m, p) == exp
