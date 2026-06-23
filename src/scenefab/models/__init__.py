#!/usr/bin/env python3

"""
数据模型模块

按域拆分的数据模型：
- narration.py: 解说风格、情感类型、解说块
- video.py: 时间范围、视频片段、情感峰值
- media.py: 字幕项、音频轨道
- project.py: 视频项目、视频分组、任务进度
- project_models.py: 项目管理器的数据模型（保持独立）

兼容层：
- 旧的 from scenefab.models import ... 导入仍可正常工作
"""

from .enums import (
    ApplicationState,
    ServiceHealth,
    ServiceStatus,
)
from .media import (
    AudioTrack,
    SubtitleItem,
)
from .narration import (
    EmotionType,
    NarrationBlock,
    NarrationStyle,
)
from .project import (
    TaskProgress,
    VideoGroup,
    VideoProject,
)
from .project_models import (
    ProjectMedia,
    ProjectMetadata,
    ProjectSettings,
    ProjectStatus,
    ProjectTimeline,
    ProjectType,
)
from .video import (
    EmotionPeak,
    TimeRange,
    VideoSegment,
)

__all__ = [
    # enums (集中定义)
    "ServiceStatus",
    "ServiceHealth",
    "ApplicationState",
    # narration
    "NarrationStyle",
    "EmotionType",
    "NarrationBlock",
    # video
    "TimeRange",
    "VideoSegment",
    "EmotionPeak",
    # media
    "SubtitleItem",
    "AudioTrack",
    # project
    "VideoProject",
    "TaskProgress",
    "VideoGroup",
    # project_models (existing)
    "ProjectStatus",
    "ProjectType",
    "ProjectMetadata",
    "ProjectSettings",
    "ProjectMedia",
    "ProjectTimeline",
]
