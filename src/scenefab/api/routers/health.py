"""
Health Router
健康检查 API
"""

from fastapi import APIRouter
from scenefab.api.schemas.models import HealthResponse

router = APIRouter()


def _get_version() -> str:
    try:
        from scenefab import __version__
        return __version__
    except Exception:
        return "3.0.0"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    # 实际应检测各服务状态
    return HealthResponse(
        status="healthy",
        version=_get_version(),
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
