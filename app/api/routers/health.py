"""
Health Router
健康检查 API
"""

from fastapi import APIRouter
from app.api.schemas.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    # 实际应检测各服务状态
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "api": "up",
            "video_processor": "up",
            "ai_service": "up",
            "storage": "up"
        }
    )


@router.get("/health/ready")
async def readiness_check():
    """就绪检查"""
    return {"ready": True}


@router.get("/health/live")
async def liveness_check():
    """存活检查"""
    return {"alive": True}
