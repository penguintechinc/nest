"""Pytest configuration and fixtures."""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from jose import jwt

import pytest
from sqlalchemy import MetaData, Table, Column, String, Integer, Text, DateTime, create_engine

# ============================================================================
# Test-mode JWT Token Generation & Validation (defined early for pytest_configure)
# ============================================================================

def _make_test_token(user_id: int = 1, email: str = "test@example.com", role: str = "admin") -> str:
    """Create a test JWT token using HS256 (NOT OIDC RS256).

    Test tokens have:
    - HS256 algorithm (matching JWT_SECRET set above)
    - tenant claim set to "test-tenant"
    - sub, email, role claims for compatibility
    - Valid expiry (24 hours)
    """
    from utils.auth import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "tenant": "test-tenant",  # Required by tenant middleware
        "scope": "",  # Compatible with OIDC scope field
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _get_auth_headers(role: str = "admin") -> dict:
    """Get Authorization headers with a valid test token."""
    token = _make_test_token(role=role)
    return {"Authorization": f"Bearer {token}"}


def _mock_tenant_middleware_for_tests():
    """Test-mode tenant middleware that validates HS256 tokens.

    This replaces the production tenant_middleware which expects OIDC RS256 tokens.
    In test mode, we accept HS256 tokens signed with JWT_SECRET.

    Returns an async function suitable for patching middleware.tenant.tenant_middleware.
    """
    async def _test_middleware():
        from quart import request, g
        from werkzeug.exceptions import Unauthorized
        from utils.auth import JWT_SECRET, JWT_ALGORITHM

        # Skip auth for health/ready/metrics
        if request.path in ["/health", "/ready", "/metrics"]:
            return

        # Skip internal routes (they have their own service auth)
        if request.path.startswith("/internal/"):
            return

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise Unauthorized(
                response={
                    "error": "auth.missing_token",
                    "message": "Authorization header with Bearer token required",
                }
            )

        token = auth_header[7:]
        try:
            # In test mode, validate with HS256 and JWT_SECRET
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            # Extract claims required by app
            tenant = decoded.get("tenant", "test-tenant")
            if not tenant:
                raise Unauthorized(
                    response={
                        "error": "auth.missing_tenant",
                        "message": "JWT missing mandatory tenant claim",
                    }
                )

            # Store in g for request scope
            g.tenant = tenant
            g.claims = decoded
        except jwt.ExpiredSignatureError:
            raise Unauthorized(
                response={
                    "error": "auth.token_expired",
                    "message": "JWT token has expired",
                }
            )
        except jwt.InvalidTokenError as e:
            raise Unauthorized(
                response={
                    "error": "auth.invalid_token",
                    "message": f"Invalid JWT token: {e}",
                }
            )

    return _test_middleware


# ============================================================================
# pytest_configure hook - runs before test collection
# This is where we patch middleware.tenant BEFORE any test files are imported
# ============================================================================

def pytest_configure(config):
    """Pytest hook: runs before test collection, before any test files are imported.

    This is the right place to patch middleware because:
    1. It runs before conftest's module-level code completes
    2. It runs before test files' module-level code runs
    3. Patches applied here are visible to all tests and all module-level code
    """
    # Set env vars first (in case any middleware reads them at import time)
    _test_db_dir = tempfile.mkdtemp(prefix="pytest_manager_")
    _test_db_path = os.path.join(_test_db_dir, "test.db")

    os.environ.setdefault("DB_TYPE", "sqlite")
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "5432")
    os.environ.setdefault("DB_NAME", _test_db_path)
    os.environ.setdefault("DB_USER", "test")
    os.environ.setdefault("DB_PASS", "test")
    os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
    os.environ.setdefault("FIELD_ENCRYPTION_KEY", "Fernet_key_placeholder_32bytes==")

    # Import middleware.tenant so we can patch it (before app.py imports it)
    import middleware.tenant

    # Patch tenant_middleware function to use HS256 validation in tests
    middleware.tenant.tenant_middleware = _mock_tenant_middleware_for_tests()


# Now safe to import app (it will see the patched middleware.tenant)
from app import create_app
from models.operations import OperationRecord
from penguin_dal import AsyncDB
from store import MemoryOperationStore, SQLOperationStore


@pytest.fixture
async def app():
    """Create a Quart test app with mocked tenant middleware.

    The test app uses a simplified HS256 token validation instead of OIDC,
    allowing tests to work without external OIDC configuration.

    The tenant_middleware is patched at session scope to accept HS256 tokens signed
    with JWT_SECRET, rather than requiring OIDC RS256 validation.
    """
    app = create_app()
    app.config["TESTING"] = True
    yield app


@pytest.fixture
async def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
async def memory_store():
    """Create an in-memory store for testing."""
    return MemoryOperationStore()


@pytest.fixture
async def sql_store():
    """Create a SQL-backed store for testing with real SQLite database."""
    # Create a temporary SQLite database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Create the schema using SQLAlchemy (idempotent via create_all)
        db_uri = f"sqlite+aiosqlite:///{db_path}"
        sync_engine = create_engine(f"sqlite:///{db_path}")
        metadata = MetaData()

        Table(
            "operations",
            metadata,
            Column("tenant", String(255), primary_key=True, nullable=False),
            Column("id", String(36), primary_key=True),
            Column("resource_name", String(255), nullable=False),
            Column("resource_type", String(100), nullable=False),
            Column("operation_type", String(100), nullable=False),
            Column("phase", String(50), nullable=False, index=True),
            Column("message", Text, nullable=False),
            Column("error", Text, nullable=True),
            Column("progress", Integer, nullable=False, default=0),
            Column("created_at", DateTime, nullable=False),
            Column("updated_at", DateTime, nullable=False),
        )
        metadata.create_all(sync_engine)
        sync_engine.dispose()

        # Create AsyncDB and reflect
        db = AsyncDB(db_uri, pool_size=5, echo=False)
        await db.reflect()
        store = SQLOperationStore(db)
        yield store
        await db.close()
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
async def store(memory_store):
    """Default store fixture (memory)."""
    return memory_store


# ============================================================================
# Shared Auth Fixtures
# ============================================================================

@pytest.fixture
def make_token():
    """Fixture providing token generation function.

    Usage: token = make_token("admin")  or  token = make_token()
    """
    return _make_test_token


@pytest.fixture
def auth_headers():
    """Fixture providing auth header generation function.

    Usage: headers = auth_headers("admin")  or  headers = auth_headers()
    Returns dict with "Authorization": "Bearer <token>"
    """
    return _get_auth_headers


@pytest.fixture
def auth_headers():
    """Fixture providing auth header generation function.

    Usage: headers = auth_headers("admin")  or  headers = auth_headers()
    Returns dict with "Authorization": "Bearer <token>"
    """
    return _get_auth_headers
