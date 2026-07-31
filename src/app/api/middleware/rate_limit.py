"""
Rate Limit Middleware
API 速率限制中间件 - 基于内存滑动窗口控制请求频率
"""

import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    API 速率限制中间件

    使用内存滑动窗口算法限制每个 Client IP 的请求频率。
    支持全局限制和特定路由严格限制。
    """

    def __init__(
        self,
        app,
        global_rate_limit: int = 120,  # 默认每分钟最多 120 次请求
        window_seconds: int = 60,
        strict_routes: dict[str, int] | None = None,  # 特殊路由限制, 如 {"/api/v1/pipeline/narrate": 10}
        excluded_paths: set[str] | None = None,
    ):
        super().__init__(app)
        self.global_rate_limit = global_rate_limit
        self.window_seconds = window_seconds
        self.strict_routes = strict_routes or {
            "/api/v1/pipeline/narrate": 10,
        }
        self.excluded_paths = excluded_paths or {
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        }

        # IP -> path -> deque of timestamps
        self._requests: dict[str, dict[str, deque[float]]] = defaultdict(
            lambda: defaultdict(deque)
        )
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # 排除路径跳过限制
        if path in self.excluded_paths:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        # 确定当前路径的限制额度
        limit = self.strict_routes.get(path, self.global_rate_limit)

        with self._lock:
            timestamps = self._requests[client_ip][path]

            # 清理超出时间窗口的记录
            cutoff = now - self.window_seconds
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= limit:
                retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
                logger.warning(
                    f"Rate limit exceeded for IP {client_ip} on path {path} ({len(timestamps)}/{limit})"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "TooManyRequests",
                        "message": "请求频率超出限制，请稍后再试",
                        "retry_after_seconds": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            timestamps.append(now)
            remaining = limit - len(timestamps)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response
