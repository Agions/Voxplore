#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

from .narration import (
    NarrationStyle,
    EmotionType,
    NarrationBlock,
)
from .video import (
    TimeRange,
    VideoSegment,
    EmotionPeak,
)
from .media import (
    SubtitleItem,
    AudioTrack,
)
from .project import (
    VideoProject,
    TaskProgress,
    VideoGroup,
)
from .project_models import (
    ProjectStatus,
    ProjectType,
    ProjectMetadata,
    ProjectSettings,
    ProjectMedia,
    ProjectTimeline,
)


__all__ = [
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