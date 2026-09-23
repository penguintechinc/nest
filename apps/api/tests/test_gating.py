from unittest.mock import patch

from gating import evaluate_category_gate


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
