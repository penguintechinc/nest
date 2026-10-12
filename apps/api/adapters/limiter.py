"""Async rate-limiter seam over penguin-limiter's synchronous ``TokenBucket``."""

import math
import time
from dataclasses import dataclass
from typing import Protocol

from penguin_limiter import MemoryStorage, TokenBucket


@dataclass(slots=True, frozen=True)
class RateDecision:
    """Outcome of one rate-limit check, shaped for ``X-RateLimit-*`` headers."""

    allowed: bool
    limit: int
    remaining: int
    reset_epoch: int


class RateLimiter(Protocol):
    """Async rate-limiter contract consumed by the hub-api rate-limit layer."""

    async def allow(self, key: str, cost: int = 1) -> RateDecision:
        """Try to consume ``cost`` tokens for ``key`` and report the decision."""
        ...


class TokenBucketRateLimiter:
    """``RateLimiter`` backed by penguin-limiter's ``TokenBucket``.

    The library has no async ``allow`` and only consumes one token per call, so this
    wrapper adds the async surface and atomic multi-token cost. All storage access is
    synchronous with no ``await`` in between, so each decision is atomic on the loop.
    """

    def __init__(
        self, limit: int, window_s: int, storage: MemoryStorage | None = None
    ) -> None:
        """Create a bucket of ``limit`` tokens that fully refills every ``window_s`` seconds."""
        if limit < 1 or window_s < 1:
            raise ValueError("limit and window_s must be >= 1")
        self._limit = limit
        self._window = window_s
        self._storage = storage if storage is not None else MemoryStorage()
        self._bucket = TokenBucket(self._storage, limit, window_s)

    async def allow(self, key: str, cost: int = 1) -> RateDecision:
        """Consume ``cost`` tokens for ``key`` atomically; deny without consuming if short."""
        if cost < 1:
            raise ValueError("cost must be >= 1")
        if cost > self._limit:
            # Can never be satisfied; do not touch the bucket.
            return RateDecision(False, self._limit, 0, int(time.time()) + self._window)

        consumed = 0
        result = self._bucket.is_allowed(key)
        if result.allowed:
            consumed = 1
        while result.allowed and consumed < cost:
            result = self._bucket.is_allowed(key)
            if result.allowed:
                consumed += 1

        if consumed == cost:
            return RateDecision(True, self._limit, result.remaining, int(time.time()))

        # Partial consumption: refund so a denied request costs nothing.
        if consumed:
            tokens, _ = self._storage.get_token_state(key)
            self._storage.set_token_state(
                key,
                min(float(self._limit), tokens + consumed),
                time.time(),
                self._window * 2,
            )
        retry_after = math.ceil(result.reset_after * (cost - consumed))
        return RateDecision(
            False, self._limit, 0, int(time.time()) + max(retry_after, 1)
        )
