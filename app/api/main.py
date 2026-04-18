"""
Voxplore FastAPI Application
Web API 层入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import projects, pipeline, export, health, plugins


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="Voxplore API",
        description="AI 第一人称视频解说 API - 让视频讲述你的故事",
        version="1.0.0",
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

    # 注册路由
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
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
