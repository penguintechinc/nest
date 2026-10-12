"""Real-path JWKS/discovery tests: do NOT fake key resolution here."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def patch_jwks_resolution() -> Iterator[None]:
    """Override the root autouse patch with a no-op so HardenedRP._signing_key runs for real."""
    yield
