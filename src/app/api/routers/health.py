"""
Health Router
健康检查 API
"""

import shutil
import tempfile

from fastapi import APIRouter

from app.api.schemas.models import HealthResponse
from app.utils.version import get_version_string

router = APIRouter()


def _probe_ffmpeg() -> str:
    return "up" if shutil.which("ffmpeg") and shutil.which("ffprobe") else "down"


def _probe_storage() -> str:
    try:
        with tempfile.TemporaryFile():
            pass
        return "up"
    except Exception:
        return "down"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查（含真实系统探针）"""
    ffmpeg_status = _probe_ffmpeg()
    storage_status = _probe_storage()

    all_up = ffmpeg_status == "up" and storage_status == "up"
    overall_status = "healthy" if all_up else "degraded"

    return HealthResponse(
        status=overall_status,
        version=get_version_string(),
        services={
            "api": "up",
            "video_processor": ffmpeg_status,
            "ai_service": "up",
            "storage": storage_status,
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
