"""Dependency and adapter contract tests for the Track A hub-api build."""

import importlib

import pytest

REQUIRED = [
    "penguin_aaa.middleware.asgi",
    "penguin_aaa.authn.oidc_rp",
    "quart_schema",
    "opentelemetry.sdk.metrics",
]


@pytest.mark.parametrize("mod", REQUIRED)
def test_required_modules_import(mod: str) -> None:
    """Every module the hub-api request stack depends on must import."""
    importlib.import_module(mod)


def test_validation_adapter_blocks_ssrf_ids() -> None:
    """Resource-id and DNS-label validators reject SSRF/path-injection input."""
    from adapters.validation import validate_dns_label, validate_resource_id

    assert validate_resource_id("tenant-1_a") == "tenant-1_a"
    for bad in ["a/b", "a b", "..", "a?x=1", "", "a\n"]:
        with pytest.raises(ValueError):
            validate_resource_id(bad)
    assert validate_dns_label("orders-db") == "orders-db"
    for bad in ["Orders", "a" * 64, "-a", "a-", "a..b"]:
        with pytest.raises(ValueError):
            validate_dns_label(bad)
