"""Outbound HTTP client (adapter for the unpublished ``penguin-http`` package)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import aiohttp


@dataclass(slots=True, frozen=True)
class HttpResult:
    """Status code and decoded JSON body of an outbound GET."""

    status: int
    body: object


class HttpClient(Protocol):
    """Async JSON-over-HTTP client contract consumed by the hub-api."""

    async def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout_s: float = 10.0,
    ) -> HttpResult:
        """GET ``url`` and return its status and decoded JSON body."""
        ...


class AiohttpClient:
    """aiohttp-backed ``HttpClient``; callers apply the SSRF guard to ``url`` first."""

    async def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout_s: float = 10.0,
    ) -> HttpResult:
        """GET ``url`` with a bounded timeout and return status plus JSON body."""
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=dict(headers or {})) as resp:
                body: object = await resp.json(content_type=None)
                return HttpResult(status=resp.status, body=body)
