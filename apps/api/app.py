"""Quart application factory and route registration."""

import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, cast

from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from quart import Quart, Response, current_app, g, jsonify, request

_api_logger = logging.getLogger("nest.api")
_tracer = trace.get_tracer("nest-api")

from adapters.limiter import RateLimiter
from auth.authz import require_scope, tenant_path_guard
from auth.rp import AsgiClaimsAdapter, HardenedRP
from auth.stack import PUBLIC_PATHS, build_asgi_stack, principal_from_claims
from catalog import CATALOG
from dto.problem import Problem, ProblemError
from handlers import (
    create_data_resource,
    create_protection_policy,
    create_search_pool,
    create_snapshot,
    delete_data_resource,
    delete_protection_policy,
    delete_search_pool,
    delete_snapshot,
    get_data_resource,
    get_search_pool,
    list_data_resources,
    list_protection_policies,
    list_search_pools,
    list_snapshots,
)
from handlers.anomaly import list_anomalies
from handlers.cost import get_cost_report, get_cost_summary
from handlers.import_handler import (
    introspect_imported_resource,
    migrate_to_managed,
    restore_data_resource,
    snapshot_data_resource,
)
from store import MemoryStore, Store

from k8s.repository import CrdRepository

# Prometheus metrics
requests_total = Counter(
    "nest_api_requests_total",
    "Total Nest API requests",
    ["method", "path", "status"],
)

request_duration = Histogram(
    "nest_api_request_duration_seconds",
    "Nest API request duration",
    ["method", "path"],
)


def create_app(
    store: Store | None = None,
    *,
    repo: CrdRepository | None = None,
    limiter: RateLimiter | None = None,
    rp: Any | None = None,
) -> Quart:
    """Create and configure the Quart application.

    Args:
        store: Persistence backend (defaults to an in-memory store).
        repo: CRD access layer seam; the concrete implementation lands in Task 12.
        limiter: Rate limiter for the ASGI layer (wired in Task 9).
        rp: Token verifier exposing ``async verify_token(raw) -> Mapping``; defaults to the
            env-configured ``HardenedRP``.
    """
    # No static route: every URL on this service is authenticated API surface.
    app = Quart(__name__, static_folder=None)

    if store is None:
        store = MemoryStore()

    # Store instance accessible in handlers
    app.config["STORE"] = store
    app.config["REPO"] = repo

    @app.before_request
    async def bridge_request() -> None:
        """Per-request setup: request ID, timer, and the validated claims -> Principal bridge.

        Runs first so ``tenant_path_guard`` (registered next) always sees ``g.principal``.
        """
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.start_time = datetime.now(timezone.utc)
        state: dict[str, Any] = cast(dict[str, Any], request.scope).get("state") or {}
        claims = state.get("claims")
        if claims is not None:
            g.principal = principal_from_claims(claims)

        _api_logger.debug(
            "request.start",
            extra={
                "method": request.method,
                "path": request.path,
                "request_id": g.request_id,
            },
        )

        principal = getattr(g, "principal", None)
        if principal is not None:
            trace.get_current_span().set_attribute("tenant", principal.tenant)

    app.before_request(tenant_path_guard)

    @app.errorhandler(ProblemError)
    async def handle_problem(e: ProblemError) -> tuple[Response, int]:
        """Render a ProblemError (401/403/...) as the RFC 7807-style Problem body."""
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        problem = Problem(
            code=e.code,
            message=e.message,
            requestId=request_id,
            docsUrl=f"https://docs.nest.penguintech.io/errors/{e.code}",
        )
        return jsonify(asdict(problem)), e.status

    @app.after_request
    async def after_request(response):
        """Record metrics and log request end."""
        method = request.method
        path = request.path or "/"
        status = response.status_code or 200
        requests_total.labels(method=method, path=path, status=status).inc()

        duration_ms = 0.0
        if hasattr(g, "start_time"):
            duration = (datetime.now(timezone.utc) - g.start_time).total_seconds()
            request_duration.labels(method=method, path=path).observe(duration)
            duration_ms = round(duration * 1000, 2)

        _api_logger.info(
            "request.end",
            extra={
                "status": status,
                "duration_ms": duration_ms,
                "request_id": getattr(g, "request_id", None),
            },
        )

        return response

    @app.errorhandler(401)
    async def handle_unauthorized(e):
        """Handle 401 Unauthorized."""
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        if hasattr(e, "response") and isinstance(e.response, dict):
            return jsonify(e.response), 401
        return (
            jsonify(
                {
                    "code": "nest.auth.unauthorized",
                    "message": "Unauthorized",
                    "requestId": request_id,
                    "docsUrl": "https://docs.nest.penguintech.io/errors/nest.auth.unauthorized",
                }
            ),
            401,
        )

    @app.errorhandler(403)
    async def handle_forbidden(e):
        """Handle 403 Forbidden."""
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        if hasattr(e, "response") and isinstance(e.response, dict):
            return jsonify(e.response), 403
        return (
            jsonify(
                {
                    "code": "nest.auth.forbidden",
                    "message": "Forbidden",
                    "requestId": request_id,
                    "docsUrl": "https://docs.nest.penguintech.io/errors/nest.auth.forbidden",
                }
            ),
            403,
        )

    @app.errorhandler(404)
    async def handle_not_found(e):
        """Handle 404 Not Found."""
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        return (
            jsonify(
                {
                    "code": "nest.api.not_found",
                    "message": "Not found",
                    "requestId": request_id,
                    "docsUrl": "https://docs.nest.penguintech.io/errors/nest.api.not_found",
                }
            ),
            404,
        )

    # Health checks (no auth required)
    @app.route("/health", methods=["GET"])
    async def health():
        """Health check endpoint."""
        return jsonify({"status": "ok"})

    @app.route("/ready", methods=["GET"])
    async def ready():
        """Readiness check endpoint."""
        return jsonify({"status": "ok"})

    @app.route("/metrics", methods=["GET"])
    async def metrics():
        """Prometheus metrics endpoint."""
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    # Authenticated API endpoints
    @app.route("/api/v1/catalog", methods=["GET"])
    @require_scope("catalog:read")
    async def catalog():
        """List available resource types."""
        return jsonify({"types": CATALOG, "meta": {"version": 1}})

    @app.route("/api/v1/versions", methods=["GET"])
    @require_scope("catalog:read")
    async def versions():
        """API version discovery."""
        return jsonify(
            {
                "versions": [
                    {
                        "version": "v1",
                        "status": "stable",
                        "specUrl": "/api/v1/openapi.json",
                    }
                ]
            }
        )

    # DataResource CRUD
    @app.route("/api/v1/tenants/<tenant_id>/data-resources", methods=["GET"])
    @require_scope("dataresource:read")
    async def list_dr(tenant_id: str):
        """List DataResources for a tenant."""
        return await list_data_resources(store)

    @app.route("/api/v1/tenants/<tenant_id>/data-resources", methods=["POST"])
    @require_scope("dataresource:write")
    async def create_dr(tenant_id: str):
        """Create a DataResource."""
        return await create_data_resource(store)

    @app.route("/api/v1/tenants/<tenant_id>/data-resources/<name>", methods=["GET"])
    @require_scope("dataresource:read")
    async def get_dr(tenant_id: str, name: str):
        """Get a DataResource."""
        return await get_data_resource(store)

    @app.route("/api/v1/tenants/<tenant_id>/data-resources/<name>", methods=["DELETE"])
    @require_scope("dataresource:delete")
    async def delete_dr(tenant_id: str, name: str):
        """Delete a DataResource."""
        return await delete_data_resource(store)

    # LRO operations
    @app.route(
        "/api/v1/tenants/<tenant_id>/data-resources/<name>/snapshot", methods=["POST"]
    )
    @require_scope("dataresource:write")
    async def snapshot_dr(tenant_id: str, name: str):
        """Snapshot a DataResource."""
        return await snapshot_data_resource(store)

    @app.route(
        "/api/v1/tenants/<tenant_id>/data-resources/<name>/restore", methods=["POST"]
    )
    @require_scope("dataresource:write")
    async def restore_dr(tenant_id: str, name: str):
        """Restore a DataResource."""
        return await restore_data_resource(store)

    @app.route(
        "/api/v1/tenants/<tenant_id>/data-resources/<name>/introspect",
        methods=["POST"],
    )
    @require_scope("dataresource:read")
    async def introspect_dr(tenant_id: str, name: str):
        """Introspect an imported DataResource."""
        return await introspect_imported_resource(store)

    @app.route(
        "/api/v1/tenants/<tenant_id>/data-resources/<name>/migrate",
        methods=["POST"],
    )
    @require_scope("dataresource:write")
    async def migrate_dr(tenant_id: str, name: str):
        """Migrate a DataResource to managed."""
        return await migrate_to_managed(store)

    # Operations (LRO status)
    @app.route("/api/v1/tenants/<tenant_id>/operations/<op_id>", methods=["GET"])
    @require_scope("operations:read")
    async def get_operation(tenant_id: str, op_id: str):
        """Get operation status."""
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        store = current_app.config["STORE"]
        try:
            op = await store.get_operation(tenant_id, op_id)
            return jsonify(op.to_dict()), 200
        except ValueError:
            return (
                jsonify(
                    {
                        "code": "nest.operation.not_found",
                        "message": "Operation not found",
                        "requestId": request_id,
                        "docsUrl": "https://docs.nest.penguintech.io/errors/nest.operation.not_found",
                    }
                ),
                404,
            )

    # VolumeSnapshot routes
    @app.route("/api/v1/tenants/<tenant_id>/snapshots", methods=["GET"])
    @require_scope("snapshot:read")
    async def list_snapshots_route(tenant_id: str):
        """List VolumeSnapshots for a tenant."""
        return await list_snapshots(store)

    @app.route("/api/v1/tenants/<tenant_id>/snapshots", methods=["POST"])
    @require_scope("snapshot:write")
    async def create_snapshot_route(tenant_id: str):
        """Create a VolumeSnapshot."""
        return await create_snapshot(store)

    @app.route("/api/v1/tenants/<tenant_id>/snapshots/<name>", methods=["DELETE"])
    @require_scope("snapshot:delete")
    async def delete_snapshot_route(tenant_id: str, name: str):
        """Delete a VolumeSnapshot."""
        return await delete_snapshot(store)

    # DataProtectionPolicy routes
    @app.route("/api/v1/tenants/<tenant_id>/protection-policies", methods=["GET"])
    @require_scope("policy:read")
    async def list_policies_route(tenant_id: str):
        """List DataProtectionPolicies for a tenant."""
        return await list_protection_policies(store)

    @app.route("/api/v1/tenants/<tenant_id>/protection-policies", methods=["POST"])
    @require_scope("policy:write")
    async def create_policy_route(tenant_id: str):
        """Create a DataProtectionPolicy."""
        return await create_protection_policy(store)

    @app.route(
        "/api/v1/tenants/<tenant_id>/protection-policies/<name>", methods=["DELETE"]
    )
    @require_scope("policy:delete")
    async def delete_policy_route(tenant_id: str, name: str):
        """Delete a DataProtectionPolicy."""
        return await delete_protection_policy(store)

    # SearchPool routes
    @app.route("/api/v1/tenants/<tenant_id>/search-pools", methods=["GET"])
    @require_scope("searchpool:read")
    async def list_pools_route(tenant_id: str):
        """List SearchPools."""
        return await list_search_pools(store)

    @app.route("/api/v1/tenants/<tenant_id>/search-pools", methods=["POST"])
    @require_scope("searchpool:write")
    async def create_pool_route(tenant_id: str):
        """Create a SearchPool."""
        return await create_search_pool(store)

    @app.route("/api/v1/tenants/<tenant_id>/search-pools/<name>", methods=["GET"])
    @require_scope("searchpool:read")
    async def get_pool_route(tenant_id: str, name: str):
        """Get a SearchPool."""
        return await get_search_pool(store)

    @app.route("/api/v1/tenants/<tenant_id>/search-pools/<name>", methods=["DELETE"])
    @require_scope("searchpool:delete")
    async def delete_pool_route(tenant_id: str, name: str):
        """Delete a SearchPool."""
        return await delete_search_pool(store)

    # Cost report routes (proxies to nest-cost-calculator)
    @app.route("/api/v1/tenants/<tenant_id>/cost-report", methods=["GET"])
    @require_scope("cost:read")
    async def cost_report(tenant_id: str):
        """Return billing history for a tenant."""
        return await get_cost_report(tenant_id)

    @app.route("/api/v1/tenants/<tenant_id>/cost-report/summary", methods=["GET"])
    @require_scope("cost:read")
    async def cost_report_summary(tenant_id: str):
        """Return aggregate billing summary for a tenant."""
        return await get_cost_summary(tenant_id)

    # Anomaly detection routes (proxies to nest-anomaly-detector; enterprise/WaddleAI gated)
    @app.route("/api/v1/tenants/<tenant_id>/anomalies", methods=["GET"])
    @require_scope("anomaly:read")
    async def anomalies(tenant_id: str):
        """Return current anomalies for a tenant's DataResources."""
        return await list_anomalies(tenant_id)

    if rp is None:
        rp = AsgiClaimsAdapter(HardenedRP.from_env())
    build_asgi_stack(app, rp=rp, limiter=limiter, public_paths=PUBLIC_PATHS)

    from telemetry import configure_telemetry

    configure_telemetry(app)

    return app
