"""
Health Router
健康检查 API
"""

from fastapi import APIRouter

from scenefab.api.schemas.models import HealthResponse
from scenefab.utils.version import get_version_string

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    # 实际应检测各服务状态
    return HealthResponse(
        status="healthy",
        version=get_version_string(),
        services={
            "api": "up",
            "video_processor": "up",
            "ai_service": "up",
            "storage": "up",
        },
    )


@router.get("/health/ready")
async def readiness_check():
    """就绪检查"""
    return {"ready": True}


@router.get("/health/live")
async def liveness_check():
    """存活检查"""
    return {"alive": True}
