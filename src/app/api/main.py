"""
SceneFab FastAPI Application
Web API 层入口
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import export, health, pipeline, plugins, projects
from app.core.exceptions import SceneFabError
from app.utils.version import get_version_string


def _configure_cors(app: FastAPI) -> None:
    """配置 CORS 中间件。

    生产环境应通过 ``CORS_ORIGINS`` 环境变量限制允许来源。默认从
    ``*`` 改为本地地址，避免未授权网站在用户浏览器里调用 API（Phase 1 · SEC-02）。

    通过 ``CORS_ALLOW_ALL=1`` 显式启用广联接；一般仅在调试时打开。
    """

    if os.getenv("CORS_ALLOW_ALL") == "1":
        cors_origins: list[str] = ["*"]
    else:
        raw = os.getenv("CORS_ORIGINS", "")
        if raw.strip():
            cors_origins = [
                item.strip() for item in raw.split(",") if item.strip()
            ]
        else:
            # 默认仅允许本地开发地址；线上显式设置 CORS_ORIGINS
            cors_origins = [
                "http://localhost",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8000",
                "http://localhost:8080",
                "http://127.0.0.1",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8080",
            ]

    allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "1") == "1"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-Requested-With",
        ],
        max_age=600,
    )


def _register_scenefab_error_handler(app: FastAPI) -> None:
    """注册 SceneFabError 异常处理器，统一返回400 + 错误详情。"""

    @app.exception_handler(SceneFabError)
    async def scenefab_error_handler(request: Request, exc: SceneFabError):
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details or {},
            },
        )


def _register_http_exception_handler(app: FastAPI) -> None:
    """注册 FastAPI HTTPException 处理器，复用其 status_code。"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "HTTPException", "message": exc.detail},
        )


def _register_general_exception_handler(app: FastAPI) -> None:
    """注册兜底异常处理器；DEBUG=1 时附带 traceback。"""
    import traceback

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": str(exc),
                "type": exc.__class__.__name__,
                "traceback": traceback.format_exc()
                if os.getenv("DEBUG") == "1"
                else None,
            },
        )


def _register_exception_handlers(app: FastAPI) -> None:
    """依次注册所有全局异常处理器。"""
    _register_scenefab_error_handler(app)
    _register_http_exception_handler(app)
    _register_general_exception_handler(app)


def _register_routers(app: FastAPI) -> None:
    """注册全部业务路由，统一挂载在 /api/v1 前缀下。"""
    app.include_router(health.router, prefix="/api/v1", tags=["健康检查"])
    app.include_router(projects.router, prefix="/api/v1", tags=["项目管理"])
    app.include_router(pipeline.router, prefix="/api/v1", tags=["流水线"])
    app.include_router(export.router, prefix="/api/v1", tags=["导出"])
    app.include_router(plugins.router, prefix="/api/v1", tags=["插件管理"])


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理器。"""
    logger.info("SceneFab API 服务正在启动...")
    yield
    logger.info("SceneFab API 服务正在关闭...")


def _configure_rate_limit(app: FastAPI) -> None:
    """配置请求速率限制中间件。"""
    from app.api.middleware.rate_limit import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)


def _configure_api_key_auth(app: FastAPI) -> None:
    """配置 API Key 鉴权中间件（Phase 1 · SEC-02）。

    行为完全由环境变量驱动，无需修改代码：

    * ``SCENEFAB_API_KEY`` 设置后，中间件生效，缺失/错误密钥返回 401。
    * ``API_REQUIRE_KEY=1`` 强制开启；未配置密钥时返回 401 避免不设
      防的产品级部署。
    * ``API_ALLOW_QUERY_KEY=1`` 仅在调试时打开；默认 false 防止日志
      把 ``?api_key=xxx`` 写进 access log。
    """
    from app.api.middleware.auth import APIKeyMiddleware

    app.add_middleware(
        APIKeyMiddleware,
        require_key=os.getenv("API_REQUIRE_KEY") == "1",
        allow_query=os.getenv("API_ALLOW_QUERY_KEY") == "1",
    )


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="SceneFab API",
        description="AI 第一人称视频解说 API - 让视频讲述你的故事",
        version=get_version_string(),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    _configure_cors(app)
    _configure_api_key_auth(app)
    _configure_rate_limit(app)
    _register_exception_handlers(app)
    _register_routers(app)

    @app.get("/")
    async def root() -> dict:
        """根路由: 返回 API metadata"""
        return {
            "name": "SceneFab API",
            "version": get_version_string(),
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# 创建应用实例
app = create_app()
