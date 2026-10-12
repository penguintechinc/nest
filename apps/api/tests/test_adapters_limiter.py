"""Tests for the async TokenBucket rate-limiter wrapper."""

import pytest
from adapters.limiter import RateDecision, TokenBucketRateLimiter


async def test_allow_under_limit() -> None:
    rl = TokenBucketRateLimiter(limit=5, window_s=60)
    d = await rl.allow("k")
    assert d.allowed and d.limit == 5 and d.remaining == 4


async def test_deny_over_limit() -> None:
    rl = TokenBucketRateLimiter(limit=2, window_s=3600)
    assert (await rl.allow("k")).allowed
    assert (await rl.allow("k")).allowed
    d = await rl.allow("k")
    assert not d.allowed and d.remaining == 0 and d.reset_epoch > 0


async def test_keys_are_independent() -> None:
    rl = TokenBucketRateLimiter(limit=1, window_s=3600)
    assert (await rl.allow("a")).allowed
    assert (await rl.allow("b")).allowed
    assert not (await rl.allow("a")).allowed


async def test_cost_greater_than_one_consumes_that_many() -> None:
    rl = TokenBucketRateLimiter(limit=5, window_s=3600)
    d = await rl.allow("k", cost=3)
    assert d.allowed and d.remaining == 2
    assert (await rl.allow("k", cost=2)).allowed
    assert not (await rl.allow("k")).allowed


async def test_denied_cost_refunds_partial_consumption() -> None:
    rl = TokenBucketRateLimiter(limit=5, window_s=3600)
    assert (await rl.allow("k", cost=3)).allowed  # 2 left
    assert not (await rl.allow("k", cost=4)).allowed  # must not eat the 2 left
    assert (await rl.allow("k", cost=2)).allowed


async def test_cost_above_limit_denied_without_consuming() -> None:
    rl = TokenBucketRateLimiter(limit=3, window_s=3600)
    assert not (await rl.allow("k", cost=4)).allowed
    assert (await rl.allow("k", cost=3)).allowed


async def test_invalid_args() -> None:
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(limit=0, window_s=1)
    rl = TokenBucketRateLimiter(limit=1, window_s=1)
    with pytest.raises(ValueError):
        await rl.allow("k", cost=0)


def test_decision_is_frozen() -> None:
    d = RateDecision(True, 1, 0, 0)
    with pytest.raises(AttributeError):
        d.allowed = False  # type: ignore[misc]
