"""
SceneFab FastAPI Application
Web API 层入口
"""

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from scenefab.api.routers import export, health, pipeline, plugins, projects
from scenefab.exceptions import SceneFabError
from scenefab.utils.version import get_version_string


def _configure_cors(app: FastAPI) -> None:
    """配置 CORS 中间件。

    生产环境应通过 CORS_ORIGINS 环境变量限制允许来源。
    """
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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


def _register_lifecycle_events(app: FastAPI) -> None:
    """注册启动/关闭生命周期钩子（当前为占位实现）。"""

    @app.on_event("startup")
    async def startup_event():
        pass

    @app.on_event("shutdown")
    async def shutdown_event():
        pass


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="SceneFab API",
        description="AI 第一人称视频解说 API - 让视频讲述你的故事",
        version=get_version_string(),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    _configure_cors(app)
    _register_exception_handlers(app)
    _register_routers(app)
    _register_lifecycle_events(app)

    return app


# 创建应用实例
app = create_app()


# 根路由
@app.get("/")
async def root():
    return {
        "name": "SceneFab API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
