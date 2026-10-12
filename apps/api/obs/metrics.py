"""Metric emission seams. Stubs here are wired to OTel in a later task."""

from __future__ import annotations


def auth_denied(reason: str) -> None:
    """Record nest_hub_auth_denied_total{reason}. No-op stub until OTel wiring lands."""
    return None
