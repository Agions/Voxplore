"""API Key authentication middleware (Phase 1 · SEC-02).

环境变量：
    * ``SCENEFAB_API_KEY`` —— 必填；为单一密钥时用此值即可以 ``Bearer``
      / ``X-API-Key`` 头部鉴权。
    * ``SCENEFAB_API_KEYS`` —— 可选；逗号分隔的多个密钥，给不同客户端签发
      不同 token，便于回收单个泄漏 token 而不影响其他客户端。

默认放行：
    * ``/``、``/docs``、``/redoc``、``/openapi.json``
    * ``/api/v1/health`` 及其 ``ready`` / ``live`` 子路径（监控系统需要）
    * 在 :py:data:`APIKeyMiddleware.DEFAULT_EXEMPT_PREFIXES` 里维护。

无密钥配置（``SCENEFAB_API_KEY`` 为空）行为：
    * ``require_key=False``（默认）：中间件放行所有请求，相当于未启用。
      适用于本地调试/CLI 工具。
    * ``require_key=True``：未配置时启动直接报错；适合生产部署明示拒绝。
"""

from __future__ import annotations

import hmac
import logging
import os
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


def _collect_keys() -> set[str]:
    """读取所有有效的 API Key（去重、去空）。

    优先取 ``SCENEFAB_API_KEY``，其次合并 ``SCENEFAB_API_KEYS``（逗号分隔）。
    返回的集合在调用时即用即构造，调用方可以每隔一段时间重新读取，
    实现热加载。
    """
    keys: set[str] = set()
    primary = os.getenv("SCENEFAB_API_KEY", "").strip()
    if primary:
        keys.add(primary)
    multi = os.getenv("SCENEFAB_API_KEYS", "").strip()
    if multi:
        for token in multi.split(","):
            token = token.strip()
            if token:
                keys.add(token)
    return keys


def _constant_time_equal(a: str, b: str) -> bool:
    """使用 :py:func:`hmac.compare_digest` 比对避免时序攻击。"""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


class APIKeyMiddleware(BaseHTTPMiddleware):
    """简单的共享密钥 API 鉴权中间件。

    用法::

        from app.api.middleware.auth import APIKeyMiddleware

        app.add_middleware(APIKeyMiddleware)

    启用后所有非豁免路径必须经 ``Authorization: Bearer <key>`` 或
    ``X-API-Key: <key>`` 头部携带有效密钥，否则返回 ``401 Unauthorized``。
    """

    DEFAULT_EXEMPT_PATHS: frozenset[str] = frozenset(
        {
            "/",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        }
    )

    DEFAULT_EXEMPT_PREFIXES: tuple[str, ...] = (
        # Swagger UI 内嵌资源
        "/static/",
    )

    HEADER_BEARER = "Authorization"
    HEADER_API_KEY = "X-API-Key"
    QUERY_KEY = "api_key"
    BEARER_PREFIX = "Bearer "

    def __init__(
        self,
        app,
        *,
        require_key: bool = False,
        allow_query: bool = False,
        exempt_paths: frozenset[str] | None = None,
        exempt_prefixes: tuple[str, ...] | None = None,
        env_loader: Callable[[], set[str]] | None = None,
    ) -> None:
        super().__init__(app)
        self._require_key = bool(require_key)
        self._allow_query = bool(allow_query)
        self._exempt_paths = (
            frozenset(exempt_paths)
            if exempt_paths is not None
            else self.DEFAULT_EXEMPT_PATHS
        )
        self._exempt_prefixes = (
            tuple(exempt_prefixes)
            if exempt_prefixes is not None
            else self.DEFAULT_EXEMPT_PREFIXES
        )
        self._env_loader = env_loader or _collect_keys

    # ──────────────────────────────────────────────────────────────────
    # 公开 helper — 让应用启动时校验必填配置
    # ──────────────────────────────────────────────────────────────────

    def has_keys(self) -> bool:
        """返回当前是否至少配置了一个有效密钥（供启动校验）。"""
        return bool(self._env_loader())

    # ──────────────────────────────────────────────────────────────────
    # Starlette 钩子
    # ──────────────────────────────────────────────────────────────────

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # 1. 静态豁免路径
        if path in self._exempt_paths or any(
            path.startswith(p) for p in self._exempt_prefixes
        ):
            return await call_next(request)

        keys = self._env_loader()

        # 2. 未配置密钥：取决于 require_key
        if not keys:
            if self._require_key:
                logger.error(
                    "API auth is required but SCENEFAB_API_KEY is unset"
                )
                return self._unauthorized(
                    detail="API key not configured on server",
                )
            return await call_next(request)

        provided = self._extract_key(request)
        if not provided:
            return self._unauthorized(detail="Missing API credentials")

        if not any(_constant_time_equal(provided, k) for k in keys):
            return self._unauthorized(detail="Invalid API key")

        return await call_next(request)

    # ──────────────────────────────────────────────────────────────────
    # 内部
    # ──────────────────────────────────────────────────────────────────

    def _extract_key(self, request: Request) -> str | None:
        # 1) Authorization: Bearer xxx
        auth_header = request.headers.get(self.HEADER_BEARER, "")
        if auth_header.startswith(self.BEARER_PREFIX):
            return auth_header[len(self.BEARER_PREFIX):].strip() or None

        # 2) X-API-Key: xxx
        api_key = request.headers.get(self.HEADER_API_KEY)
        if api_key:
            return api_key.strip() or None

        # 3) ?api_key=xxx （默认禁用，避免日志泄露密钥）
        if self._allow_query:
            try:
                raw = request.query_params.get(self.QUERY_KEY)
            except Exception:  # pragma: no cover - 解析失败时静默
                raw = None
            if raw:
                # ``parse_qs`` 会返回 list，这里取第一个元素并去空白。
                if isinstance(raw, (list, tuple)):
                    raw = raw[0] if raw else ""
                if isinstance(raw, str):
                    return raw.strip() or None
        return None

    @staticmethod
    def _unauthorized(
        detail: str = "Unauthorized",
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        headers = {"WWW-Authenticate": 'Bearer realm="scenefab"'}
        if extra_headers:
            headers.update(extra_headers)
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized",
                "message": detail,
            },
            headers=headers,
        )


__all__ = ["APIKeyMiddleware"]
