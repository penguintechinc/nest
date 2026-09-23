"""Two-layer DataResource category gate: PostHog rollout flag + license tier.

Both layers fail safe. If the flag backend is unreachable the last-known cached
value is used; a never-seen flag defaults OFF (critical-rules.md Feature Flags).
A gate failure never raises into the request path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Tier ordering for entitlement comparison.
_TIER_RANK = {"free": 0, "professional": 1, "pro": 1, "enterprise": 2}

# Phase 0 entitlement: analytics needs Professional; everything else is Free.
_MIN_TIER = {"analytics": "professional"}

# Last-known flag values, per (flag, tenant), for graceful degradation.
_flag_cache: dict[tuple[str, str], bool] = {}


@dataclass(slots=True)
class GateDecision:
    """Outcome of a category gate check."""

    allowed: bool
    code: str
    message: str


def _flag_enabled(flag_key: str, tenant: str) -> bool:
    """Return whether a PostHog flag is enabled for a tenant.

    Wraps the PostHog SDK; isolated so tests patch it. Follows the
    integrating-license-server skill for client init (env-configured).
    """
    import posthog

    posthog.project_api_key = os.environ["POSTHOG_API_KEY"]
    posthog.host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")
    return bool(posthog.feature_enabled(flag_key, tenant) or False)


def _flag_or_cached(flag_key: str, tenant: str) -> bool:
    """Evaluate a flag, falling back to the last-known cached value (else OFF)."""
    try:
        value = _flag_enabled(flag_key, tenant)
        _flag_cache[(flag_key, tenant)] = value
        return value
    except Exception:  # noqa: BLE001 - intentionally broad catch for fail-safe
        return _flag_cache.get((flag_key, tenant), False)


def evaluate_category_gate(category: str, tier: str, tenant: str) -> GateDecision:
    """Run the two-layer gate for a category. Never raises."""
    # Layer 1: operational rollout flag.
    if not _flag_or_cached(f"nest.{category}", tenant):
        return GateDecision(
            False,
            "nest.gate.flag_disabled",
            f"The '{category}' module is not enabled in this environment.",
        )
    # Layer 2: license tier entitlement.
    required = _MIN_TIER.get(category)
    if required is not None and _TIER_RANK.get(tier, 0) < _TIER_RANK[required]:
        return GateDecision(
            False,
            "nest.gate.tier_required",
            f"The '{category}' module requires the {required} tier.",
        )
    return GateDecision(True, "", "")
