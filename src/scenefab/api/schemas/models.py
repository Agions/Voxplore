"""
API Schemas
Pydantic 模型定义
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from scenefab.models.narration import EmotionType
from scenefab.services.export.export_manager import ExportFormat as ManagerExportFormat

# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

# EmotionType 已统一到 scenefab.models.narration


class InterleaveModeAPI(str, Enum):
    NARRATION_PRIORITY = "narration_priority"
    ORIGINAL_PRIORITY = "original_priority"
    EMOTIONAL_BURST = "emotional_burst"
    MINIMALIST = "minimalist"
    CINEMATIC = "cinematic"


# ─────────────────────────────────────────────────────────────
# Project Schemas
# ─────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: str
    updated_at: str
    status: str


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


# ─────────────────────────────────────────────────────────────
# Pipeline Schemas
# ─────────────────────────────────────────────────────────────

class NarrationRequest(BaseModel):
    project_id: str
    video_url: str                      # 视频 URL 或本地路径
    emotion: EmotionType = EmotionType.HEALING
    interleave_mode: InterleaveModeAPI = InterleaveModeAPI.CINEMATIC
    voice_id: str | None = None       # 指定音色
    max_duration: float | None = None  # 最大解说时长（秒）


class PipelineStatus(BaseModel):
    task_id: str
    status: str                          # pending, processing, completed, failed
    progress: float = 0.0                 # 0-100
    current_step: str                     # 当前步骤
    estimated_remaining: float | None  # 预估剩余时间（秒）
    result_url: str | None = None      # 完成后的结果 URL
    error: str | None = None


# ─────────────────────────────────────────────────────────────
# Export Schemas
# ─────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    project_id: str
    format: ManagerExportFormat = ManagerExportFormat.MP4
    quality: str = "high"                # low, medium, high, ultra
    resolution: str = "1080p"            # 720p, 1080p, 4k
    fps: int = 30
    codec: str = "h264"                 # h264, h265, vp9
    output_path: str | None = None


class ExportResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    download_url: str | None = None


# ─────────────────────────────────────────────────────────────
# Health Schemas
# ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
