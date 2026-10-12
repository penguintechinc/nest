"""Pytest fixtures for Nest API tests."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import os  # noqa: E402
from typing import Any  # noqa: E402
from unittest.mock import (
    MagicMock,  # noqa: E402
    patch,  # noqa: E402
)

import pytest  # noqa: E402
from app import create_app  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey  # noqa: E402
from store.store import MemoryStore  # noqa: E402

from tests.tokens import (  # noqa: E402
    _generate_test_keypair,
    _mint_token,
)


async def _fake_signing_key(self: Any, raw_token: str) -> RSAPublicKey:
    """Stand-in for HardenedRP._signing_key: resolve the session test public key offline."""
    return _generate_test_keypair()[1]


@pytest.fixture(scope="session", autouse=True)
def setup_oidc_env() -> None:
    """Set up OIDC environment variables for tests."""
    os.environ["OIDC_JWKS_URL"] = "https://nest.penguintech.io/.well-known/jwks.json"
    os.environ["OIDC_ISSUER"] = "https://nest.penguintech.io"
    os.environ["OIDC_AUDIENCE"] = "nest-api"


@pytest.fixture(scope="session", autouse=True)
def patch_jwks_resolution():  # type: ignore[no-untyped-def]
    """Point the hardened RP's key resolution at the test keypair for all tests.

    Only key *fetching* is faked; signature/alg/iss/aud/exp/nbf validation runs for real.
    """
    with patch("auth.rp.HardenedRP._signing_key", new=_fake_signing_key):
        yield


@pytest.fixture(scope="session", autouse=True)
def patch_kubernetes_client():  # type: ignore[no-untyped-def]
    """Patch Kubernetes client initialization for all tests.

    This prevents the restore handler from trying to load in-cluster config,
    which fails in test environments. All K8s API calls are mocked.
    """

    def mock_load_incluster_config():  # type: ignore[no-untyped-def]
        """Mock load_incluster_config to do nothing instead of raising."""

    def mock_custom_objects_api(api_client):  # type: ignore[no-untyped-def]
        """Return a mock CustomObjectsApi."""
        mock_api = MagicMock()
        # Mock list_namespaced_custom_object to return a sample backup
        # so the handler can proceed with restore
        mock_api.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {
                        "name": "backup-001",
                        "creationTimestamp": "2024-01-01T00:00:00Z",
                    },
                    "spec": {"includedNamespaces": ["default"]},
                }
            ]
        }
        # Mock create_namespaced_custom_object to succeed
        mock_api.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "restore-001"},
        }
        return mock_api

    def mock_core_v1_api(api_client):  # type: ignore[no-untyped-def]
        """Return a mock CoreV1Api."""
        mock_api = MagicMock()
        # Mock create_namespaced_persistent_volume_claim to succeed
        mock_api.create_namespaced_persistent_volume_claim.return_value = {
            "metadata": {"name": "pvc-restored"},
        }
        return mock_api

    def mock_api_client():  # type: ignore[no-untyped-def]
        """Return a mock ApiClient."""
        return MagicMock()

    with (
        patch(
            "kubernetes.config.load_incluster_config",
            side_effect=mock_load_incluster_config,
        ),
        patch("kubernetes.client.ApiClient", side_effect=mock_api_client),
        patch(
            "kubernetes.client.CustomObjectsApi",
            side_effect=mock_custom_objects_api,
        ),
        patch("kubernetes.client.CoreV1Api", side_effect=mock_core_v1_api),
    ):
        yield


@pytest.fixture(autouse=True)
def allow_category_gate():  # type: ignore[no-untyped-def]
    """Default the DataResource category gate to ALLOW for all tests.

    The gate (Task 6) defaults fail-safe OFF, which would 403 every existing
    create-path test that predates gating. test_gating.py's handler-integration
    tests override this per-test with a nested patch on the same target.
    """
    from gating import GateDecision

    with patch(
        "handlers.dataresource.evaluate_category_gate",
        return_value=GateDecision(True, "", ""),
    ):
        yield


@pytest.fixture
async def client():  # type: ignore[no-untyped-def]
    """Create a test app with fresh MemoryStore."""
    store = MemoryStore()
    app = create_app(store)

    # Deliberately not `async with`: that sets preserve_context, which crashes when the ASGI
    # auth stack answers (401/403/preflight) before the request ever reaches Quart.
    yield app.test_client()


@pytest.fixture
async def store():  # type: ignore[no-untyped-def]
    """Create a fresh MemoryStore for each test."""
    return MemoryStore()


@pytest.fixture
def bearer_token() -> str:
    """Generate a valid RS256 bearer token for testing.

    Returns a pro-tier token with admin scope.
    """
    return _mint_token(sub="test-sub", tenant="test-tenant", tier="pro")


@pytest.fixture
def free_tier_token() -> str:
    """Generate a free-tier RS256 bearer token for testing."""
    return _mint_token(sub="test-sub", tenant="test-tenant", tier="free")
