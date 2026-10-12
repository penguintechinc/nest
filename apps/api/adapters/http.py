"""Outbound HTTP client (adapter for the unpublished ``penguin-http`` package)."""

import json
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

import aiohttp

DEFAULT_MAX_BODY_BYTES = 1_048_576
_ALLOWED_SCHEMES = frozenset({"http", "https"})


class UnsafeUrlError(ValueError):
    """Raised when a URL fails the SSRF guard (scheme, userinfo, or host allowlist)."""


class ResponseTooLargeError(Exception):
    """Raised when a response body exceeds the configured maximum size."""


@dataclass(slots=True, frozen=True)
class HttpResult:
    """Status code and decoded JSON body of an outbound GET (``None`` body for 3xx)."""

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


def check_url(url: str, allowed_hosts: Collection[str]) -> None:
    """Raise ``UnsafeUrlError`` unless ``url`` is http(s), has no userinfo, and host is allowlisted."""
    parts = urlsplit(url)
    if parts.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError("scheme not allowed")
    if parts.username is not None or parts.password is not None:
        raise UnsafeUrlError("userinfo not allowed")
    host = (parts.hostname or "").lower()
    if not host or host not in {h.lower() for h in allowed_hosts}:
        raise UnsafeUrlError("host not allowlisted")


class AiohttpClient:
    """aiohttp-backed ``HttpClient`` with SSRF guard, no redirects, and capped body size."""

    def __init__(
        self,
        allowed_hosts: Collection[str],
        *,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        """Create a client that only ever contacts ``allowed_hosts`` (fail-closed if empty)."""
        self._allowed_hosts = frozenset(h.lower() for h in allowed_hosts)
        self._max_body_bytes = max_body_bytes

    async def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout_s: float = 10.0,
    ) -> HttpResult:
        """GET ``url`` after the SSRF guard; never follow redirects; cap body and time.

        Raises ``UnsafeUrlError`` before any I/O for a disallowed URL,
        ``ResponseTooLargeError`` past the body cap, ``TimeoutError`` past ``timeout_s``,
        and ``ValueError`` for a non-JSON body.
        """
        check_url(url, self._allowed_hosts)
        timeout = aiohttp.ClientTimeout(total=timeout_s, connect=timeout_s)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url, headers=dict(headers or {}), allow_redirects=False
            ) as resp:
                if 300 <= resp.status < 400:
                    # Redirect targets bypass the host allowlist; surface, never follow.
                    return HttpResult(status=resp.status, body=None)
                declared = resp.content_length
                if declared is not None and declared > self._max_body_bytes:
                    raise ResponseTooLargeError("declared body exceeds limit")
                chunks: list[bytes] = []
                size = 0
                async for chunk in resp.content.iter_chunked(65536):
                    size += len(chunk)
                    if size > self._max_body_bytes:
                        raise ResponseTooLargeError("body exceeds limit")
                    chunks.append(chunk)
                body: object = json.loads(b"".join(chunks))
                return HttpResult(status=resp.status, body=body)
