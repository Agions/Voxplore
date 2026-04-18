"""
API Schemas
Pydantic 模型定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class EmotionType(str, Enum):
    HEALING = "healing"       # 治愈
    SUSPENSE = "suspense"    # 悬疑
    MOTIVATIONAL = "motivational"  # 励志
    NOSTALGIC = "nostalgic"   # 怀旧
    ROMANTIC = "romantic"     # 浪漫


class ExportFormat(str, Enum):
    MP4 = "mp4"
    JIANYIN = "jianyin"       # 剪映草稿
    PREMIERE_XML = "premiere_xml"


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
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    status: str


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


# ─────────────────────────────────────────────────────────────
# Pipeline Schemas
# ─────────────────────────────────────────────────────────────

class NarrationRequest(BaseModel):
    project_id: str
    video_url: str                      # 视频 URL 或本地路径
    emotion: EmotionType = EmotionType.HEALING
    interleave_mode: InterleaveModeAPI = InterleaveModeAPI.CINEMATIC
    voice_id: Optional[str] = None       # 指定音色
    max_duration: Optional[float] = None  # 最大解说时长（秒）


class PipelineStatus(BaseModel):
    task_id: str
    status: str                          # pending, processing, completed, failed
    progress: float = 0.0                 # 0-100
    current_step: str                     # 当前步骤
    estimated_remaining: Optional[float]  # 预估剩余时间（秒）
    result_url: Optional[str] = None      # 完成后的结果 URL
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Export Schemas
# ─────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    project_id: str
    format: ExportFormat = ExportFormat.MP4
    quality: str = "high"                # low, medium, high
    options: Optional[Dict[str, Any]] = None


class ExportResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    download_url: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Health Schemas
# ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]
