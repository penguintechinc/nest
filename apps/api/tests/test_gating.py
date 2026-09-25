from unittest.mock import patch

import pytest
from gating import evaluate_category_gate
from handlers import dataresource as dataresource_handler


def _flag_on(*_a, **_k):
    return True


def _flag_off(*_a, **_k):
    return False


def _flag_raises(*_a, **_k):
    raise RuntimeError("posthog unreachable")


def test_core_category_allowed_when_flag_on():
    with patch("gating._flag_enabled", _flag_on):
        d = evaluate_category_gate("database", tier="free", tenant="t1")
    assert d.allowed


def test_flag_off_denies():
    with patch("gating._flag_enabled", _flag_off):
        d = evaluate_category_gate("database", tier="free", tenant="t1")
    assert not d.allowed
    assert d.code == "nest.gate.flag_disabled"


def test_analytics_requires_professional():
    with patch("gating._flag_enabled", _flag_on):
        free = evaluate_category_gate("analytics", tier="free", tenant="t1")
        pro = evaluate_category_gate("analytics", tier="pro", tenant="t1")
    assert not free.allowed and free.code == "nest.gate.tier_required"
    assert pro.allowed


def test_posthog_failure_is_failsafe_off():
    # Unreachable flag backend → treated as OFF (cached default), never crash.
    with patch("gating._flag_enabled", _flag_raises):
        d = evaluate_category_gate("database", tier="free", tenant="t1")
    assert not d.allowed
    assert d.code == "nest.gate.flag_disabled"


@pytest.mark.asyncio
async def test_create_denied_when_flag_off(client, bearer_token):
    with patch("handlers.dataresource.evaluate_category_gate") as gate:
        from gating import GateDecision

        gate.return_value = GateDecision(False, "nest.gate.flag_disabled", "off")
        resp = await client.post(
            "/api/v1/tenants/test-tenant/data-resources",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={
                "name": "x",
                "type": "postgres",
                "class": "std",
                "origination": "managed",
            },
        )
    assert resp.status_code == 403
    body = await resp.get_json()
    assert body["code"] == "nest.gate.flag_disabled"


@pytest.mark.asyncio
async def test_create_allowed_when_gate_passes(client, bearer_token):
    with patch("handlers.dataresource.evaluate_category_gate") as gate:
        from gating import GateDecision

        gate.return_value = GateDecision(True, "", "")
        resp = await client.post(
            "/api/v1/tenants/test-tenant/data-resources",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={
                "name": "x",
                "type": "postgres",
                "class": "std",
                "origination": "managed",
            },
        )
    assert resp.status_code == 202


# --- Finding 1 regression: analytics tier gate reachable via the create path ---
#
# Before the fix, dataresource.py hardcoded valid_types to 8 engine types and
# 400'd anything else before evaluate_category_gate ever ran, so the
# analytics -> Professional tier gate was unreachable via the API for
# clickhouse/warehouse-trino/lakehouse-iceberg. These tests wire in the REAL
# evaluate_category_gate (flag layer forced on via gating._flag_enabled) so a
# wrong patch target would surface as a flag_disabled 403 instead of the
# expected tier_required 403/202 split, rather than a false green.


@pytest.mark.asyncio
async def test_create_denied_free_tier_analytics_type(client, free_tier_token):
    """A free-tier token hitting an analytics engine type gets 403 tier_required."""
    with (
        patch.object(
            dataresource_handler, "evaluate_category_gate", evaluate_category_gate
        ),
        patch("gating._flag_enabled", return_value=True),
    ):
        resp = await client.post(
            "/api/v1/tenants/test-tenant/data-resources",
            headers={"Authorization": f"Bearer {free_tier_token}"},
            json={
                "name": "ch-free",
                "type": "clickhouse",
                "class": "std",
                "origination": "managed",
            },
        )
    assert resp.status_code == 403
    body = await resp.get_json()
    assert body["code"] == "nest.gate.tier_required"
    assert "professional" in body["message"]


@pytest.mark.asyncio
async def test_create_allowed_pro_tier_analytics_type(client, bearer_token):
    """A pro/professional-tier token hitting an analytics engine type gets 202."""
    with (
        patch.object(
            dataresource_handler, "evaluate_category_gate", evaluate_category_gate
        ),
        patch("gating._flag_enabled", return_value=True),
    ):
        resp = await client.post(
            "/api/v1/tenants/test-tenant/data-resources",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={
                "name": "ch-pro",
                "type": "clickhouse",
                "class": "std",
                "origination": "managed",
            },
        )
    assert resp.status_code == 202
