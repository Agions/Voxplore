"""
SceneFab FastAPI Application
Web API 层入口
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from scenefab.api.routers import export, health, pipeline, plugins, projects
from scenefab.exceptions import SceneFabError


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""

    def _get_version() -> str:
        try:
            from scenefab import __version__

            return __version__
        except Exception:
            return "1.0.0"

    app = FastAPI(
        title="SceneFab API",
        description="AI 第一人称视频解说 API - 让视频讲述你的故事",
        version=_get_version(),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS 配置（生产环境应通过 CORS_ORIGINS 环境变量限制）
    import os

    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 全局异常处理器 ─────────────────────────────────────────────
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

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "HTTPException", "message": exc.detail},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        import os
        import traceback

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

    # ── 注册路由 ─────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api/v1", tags=["健康检查"])
    app.include_router(projects.router, prefix="/api/v1", tags=["项目管理"])
    app.include_router(pipeline.router, prefix="/api/v1", tags=["流水线"])
    app.include_router(export.router, prefix="/api/v1", tags=["导出"])
    app.include_router(plugins.router, prefix="/api/v1", tags=["插件管理"])

    # 启动事件
    @app.on_event("startup")
    async def startup_event():
        pass

    @app.on_event("shutdown")
    async def shutdown_event():
        pass

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
