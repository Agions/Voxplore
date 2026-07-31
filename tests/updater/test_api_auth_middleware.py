#!/usr/bin/env python3
"""Tests for :pymod:`app.api.middleware.auth` (Phase 1 · SEC-02)."""

from __future__ import annotations

import os
from collections.abc import Callable
from unittest.mock import patch

import pytest


@pytest.fixture
def clear_env(monkeypatch):
    """确保每个测试都从干净的环境变量开始。"""
    for var in ("SCENEFAB_API_KEY", "SCENEFAB_API_KEYS", "API_REQUIRE_KEY"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def _build_middleware(
    *,
    keys: list[str] | None = None,
    require_key: bool = False,
    allow_query: bool = False,
) -> object:
    """构造一个实例，注入 env loader 便于 deterministic 测试。"""

    from app.api.middleware.auth import APIKeyMiddleware

    class _StubApp:
        async def __call__(self, scope, receive, send):
            pass

    def loader(keys=keys): return set(keys or [])

    return APIKeyMiddleware(
        _StubApp(),
        require_key=require_key,
        allow_query=allow_query,
        env_loader=loader,
    )


class _RequestBuilder:
    """Mock :class:`starlette.requests.Request` for the middleware dispatch."""

    def __init__(self, headers: dict[str, str] | None = None, query: str = ""):
        self._headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.url = type(
            "URL", (), {"path": "/api/v1/pipeline/narrate", "query": query})()
        self.client = type("Client", (), {"host": "127.0.0.1"})()

    def headers(self):
        return self._headers

    @property
    def query_params(self):
        from urllib.parse import parse_qs

        return parse_qs(self.url.query)


def _request(headers=None, query: str = ""):
    req = _RequestBuilder(headers=headers or {}, query=query)
    # starlette's Request uses property descriptors; bind dynamically
    req_cls = type(
        "FakeRequest",
        (),
        {
            "url": property(lambda self: req.url),
            "headers": property(lambda self: type(
                "H", (), {"get": lambda _, k,
                          default="": self._headers.get(k.lower(), default)}
            )()),
            "query_params": property(lambda self: req.query_params),
            "client": property(lambda self: req.client),
            "_headers": req._headers,
        },
    )
    return req_cls()


def _bypass_response() -> object:
    """``call_next`` 返回的伪响应。"""

    class _Resp:
        pass

    return _Resp()


class _BypassResponse:
    """稳定可比较的 stub 响应类型（避免工厂函数生成新类导致 isinstance 失效）。"""

    pass


class TestMiddlewarePassThrough:
    """未配置密钥时的行为。"""

    @pytest.mark.asyncio
    async def test_no_key_passes_through_when_not_required(self, clear_env):
        from app.api.middleware.auth import _collect_keys

        assert _collect_keys() == set()

        async def call_next(_):
            return _BypassResponse()

        mw = _build_middleware()
        result = await mw.dispatch(_request(), call_next)
        assert isinstance(result, _BypassResponse)


class TestMiddlewareReject:
    """错误或缺失凭证应返回 401。"""

    @pytest.mark.asyncio
    async def test_rejects_missing_credentials(self, clear_env):
        async def call_next(_):
            return _bypass_response()

        mw = _build_middleware(keys=["secret"])

        called = False

        async def guarded_call_next(req):
            nonlocal called
            called = True
            return _BypassResponse()

        resp = await mw.dispatch(_request(), guarded_call_next)
        assert called is False
        assert getattr(resp, "status_code", None) == 401

    @pytest.mark.asyncio
    async def test_rejects_invalid_credentials(self, clear_env):
        mw = _build_middleware(keys=["right-key"])
        resp = await mw.dispatch(
            _request(headers={"Authorization": "Bearer wrong-key"}),
            lambda _: _bypass_response(),
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_require_key_returns_401_without_env(self, clear_env):
        mw = _build_middleware(require_key=True)  # no keys configured
        resp = await mw.dispatch(_request(), lambda _: _bypass_response())
        assert resp.status_code == 401


class TestMiddlewareAccept:
    """成功路径。"""

    @pytest.mark.asyncio
    async def test_accepts_bearer(self, clear_env):
        mw = _build_middleware(keys=["topsecret"])
        called = False

        async def cn(_):
            nonlocal called
            called = True
            return _BypassResponse()

        resp = await mw.dispatch(
            _request(headers={"Authorization": "Bearer topsecret"}),
            cn,
        )
        assert called is True
        assert isinstance(resp, _BypassResponse)

    @pytest.mark.asyncio
    async def test_accepts_x_api_key(self, clear_env):
        mw = _build_middleware(keys=["topsecret"])
        called = False

        async def cn(_):
            nonlocal called
            called = True
            return _BypassResponse()

        resp = await mw.dispatch(
            _request(headers={"X-API-Key": "topsecret"}),
            cn,
        )
        assert called is True
        assert isinstance(resp, _BypassResponse)

    @pytest.mark.asyncio
    async def test_accepts_query_when_enabled(self, clear_env):
        mw = _build_middleware(keys=["topsecret"], allow_query=True)
        called = False

        async def cn(_):
            nonlocal called
            called = True
            return _BypassResponse()

        resp = await mw.dispatch(_request(query="api_key=topsecret"), cn)
        assert called is True
        assert isinstance(resp, _BypassResponse)

    @pytest.mark.asyncio
    async def test_rejects_query_when_disabled(self, clear_env):
        mw = _build_middleware(keys=["topsecret"], allow_query=False)

        async def cn(_):
            return _bypass_response()

        resp = await mw.dispatch(_request(query="api_key=topsecret"), cn)
        assert getattr(resp, "status_code", None) == 401


class TestExemptPaths:
    """白名单路径不走鉴权。"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        ],
    )
    async def test_exempt_paths_pass(self, clear_env, path, monkeypatch):
        # Re-build request with custom path
        from app.api.middleware.auth import APIKeyMiddleware
        from urllib.parse import parse_qs

        class _StubApp:
            async def __call__(self, scope, receive, send):
                pass

        def loader():
            return {"secret"}

        mw = APIKeyMiddleware(_StubApp(), env_loader=loader)

        class Req:
            url = type("U", (), {"path": path, "query": ""})()
            headers = type(
                "H", (), {"get": lambda _, k, default="": default}
            )()
            query_params = parse_qs("")
            client = type("C", (), {"host": "127.0.0.1"})()

        called = False

        async def cn2(_):
            nonlocal called
            called = True
            return _BypassResponse()

        await mw.dispatch(Req(), cn2)
        assert called is True


class TestEnvLoader:
    """环境变量加载器独立测试。"""

    def test_loads_single_key(self, monkeypatch):
        monkeypatch.setenv("SCENEFAB_API_KEY", "K1")
        from app.api.middleware.auth import _collect_keys

        assert _collect_keys() == {"K1"}

    def test_loads_multiple_keys_deduplicated(self, monkeypatch):
        monkeypatch.setenv("SCENEFAB_API_KEY", "K1")
        monkeypatch.setenv("SCENEFAB_API_KEYS", "K2,K1,K3")
        from app.api.middleware.auth import _collect_keys

        assert _collect_keys() == {"K1", "K2", "K3"}

    def test_empty_env_returns_empty(self, monkeypatch):
        monkeypatch.delenv("SCENEFAB_API_KEY", raising=False)
        monkeypatch.delenv("SCENEFAB_API_KEYS", raising=False)
        from app.api.middleware.auth import _collect_keys

        assert _collect_keys() == set()

    def test_whitespace_and_empty_entries_skipped(self, monkeypatch):
        monkeypatch.setenv("SCENEFAB_API_KEYS", "K1, , ,K2,, ,")
        from app.api.middleware.auth import _collect_keys

        assert _collect_keys() == {"K1", "K2"}
