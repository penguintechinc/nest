"""Tests for the hardened aiohttp client (SSRF guard, redirects, timeout, size cap)."""

import asyncio
from collections.abc import AsyncIterator

import pytest
from adapters.http import (
    AiohttpClient,
    ResponseTooLargeError,
    UnsafeUrlError,
)
from aiohttp import web
from aiohttp.test_utils import TestServer


@pytest.fixture
async def server() -> AsyncIterator[tuple[TestServer, dict[str, int]]]:
    hits = {"internal": 0}

    async def ok(_: web.Request) -> web.Response:
        return web.json_response({"a": 1})

    async def text(_: web.Request) -> web.Response:
        return web.Response(text="not json", content_type="text/plain")

    async def slow(_: web.Request) -> web.Response:
        await asyncio.sleep(2)
        return web.json_response({})

    async def internal(_: web.Request) -> web.Response:
        hits["internal"] += 1
        return web.json_response({"secret": True})

    async def redirect(request: web.Request) -> web.Response:
        raise web.HTTPFound(location="/internal")

    async def big(_: web.Request) -> web.Response:
        return web.json_response({"x": "y" * 5000})

    async def chunked_big(request: web.Request) -> web.StreamResponse:
        resp = web.StreamResponse()
        await resp.prepare(request)  # no Content-Length: chunked
        for _ in range(10):
            await resp.write(b"x" * 1000)
        await resp.write_eof()
        return resp

    app = web.Application()
    app.add_routes(
        [
            web.get("/ok", ok),
            web.get("/text", text),
            web.get("/slow", slow),
            web.get("/internal", internal),
            web.get("/redir", redirect),
            web.get("/big", big),
            web.get("/chunked", chunked_big),
        ]
    )
    srv = TestServer(app, host="127.0.0.1")
    await srv.start_server()
    try:
        yield srv, hits
    finally:
        await srv.close()


def _client(srv: TestServer, **kw: int) -> AiohttpClient:
    return AiohttpClient(["127.0.0.1"], **kw)


async def test_200_json(server: tuple[TestServer, dict[str, int]]) -> None:
    srv, _ = server
    res = await _client(srv).get_json(str(srv.make_url("/ok")))
    assert res.status == 200 and res.body == {"a": 1}


async def test_non_json_raises(server: tuple[TestServer, dict[str, int]]) -> None:
    srv, _ = server
    with pytest.raises(ValueError):
        await _client(srv).get_json(str(srv.make_url("/text")))


async def test_timeout_raises(server: tuple[TestServer, dict[str, int]]) -> None:
    srv, _ = server
    with pytest.raises(TimeoutError):
        await _client(srv).get_json(str(srv.make_url("/slow")), timeout_s=0.2)


async def test_redirect_not_followed(server: tuple[TestServer, dict[str, int]]) -> None:
    srv, hits = server
    res = await _client(srv).get_json(str(srv.make_url("/redir")))
    assert res.status == 302 and res.body is None
    assert hits["internal"] == 0


async def test_declared_oversize_rejected(
    server: tuple[TestServer, dict[str, int]],
) -> None:
    srv, _ = server
    with pytest.raises(ResponseTooLargeError):
        await _client(srv, max_body_bytes=1000).get_json(str(srv.make_url("/big")))


async def test_streamed_oversize_rejected(
    server: tuple[TestServer, dict[str, int]],
) -> None:
    srv, _ = server
    with pytest.raises(ResponseTooLargeError):
        await _client(srv, max_body_bytes=5000).get_json(str(srv.make_url("/chunked")))


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://127.0.0.1/",
        "http://evil.example/ok",
        "http://user:pw@127.0.0.1/ok",
        "http:///ok",
        "//127.0.0.1/ok",
    ],
)
async def test_ssrf_guard_runs_before_request(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        await AiohttpClient(["127.0.0.1"]).get_json(url)


async def test_empty_allowlist_is_fail_closed() -> None:
    with pytest.raises(UnsafeUrlError):
        await AiohttpClient([]).get_json("http://127.0.0.1/ok")
