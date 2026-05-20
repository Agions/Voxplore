"""
Voxplore FastAPI Application
Web API 层入口
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from voxplore.api.routers import projects, pipeline, export, health, plugins
from voxplore.core.exceptions import VoxploreError


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="Voxplore API",
        description="AI 第一人称视频解说 API - 让视频讲述你的故事",
        version="1.0.1",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 全局异常处理器 ─────────────────────────────────────────────
    @app.exception_handler(VoxploreError)
    async def voxplore_error_handler(request: Request, exc: VoxploreError):
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
        # 暴露详细错误（开发环境）
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": str(exc),
                "type": exc.__class__.__name__,
                "traceback": traceback.format_exc(),
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
        "name": "Voxplore API",
        "version": "1.0.1",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
