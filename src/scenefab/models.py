#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据模型（兼容层）

.. deprecated::
    请从 scenefab.models 导入（已迁移至域拆分模块）：
    - scenefab.models.narration: NarrationStyle, EmotionType, NarrationBlock
    - scenefab.models.video: TimeRange, VideoSegment, EmotionPeak
    - scenefab.models.media: SubtitleItem, AudioTrack
    - scenefab.models.project: VideoProject, VideoGroup, TaskProgress

使用示例：
    from scenefab.models import VideoSegment, NarrationBlock
    # 等价于
    from scenefab.models.video import VideoSegment
    from scenefab.models.narration import NarrationBlock
"""
from __future__ import annotations

import warnings

warnings.warn(
    "scenefab.models is deprecated, import from scenefab.models.narration, "
    "scenefab.models.video, scenefab.models.media, or scenefab.models.project instead",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all public interfaces (direct imports to avoid circular ref)
from .models.narration import (
    NarrationStyle,
    EmotionType,
    NarrationBlock,
)
from .models.video import (
    TimeRange,
    VideoSegment,
    EmotionPeak,
)
from .models.media import (
    SubtitleItem,
    AudioTrack,
)
from .models.project import (
    VideoProject,
    TaskProgress,
    VideoGroup,
)
from .models.project_models import (
    ProjectStatus,
    ProjectType,
    ProjectMetadata,
    ProjectSettings,
    ProjectMedia,
    ProjectTimeline,
)

__all__ = [
    "NarrationStyle",
    "EmotionType",
    "TimeRange",
    "VideoSegment",
    "EmotionPeak",
    "NarrationBlock",
    "SubtitleItem",
    "AudioTrack",
    "VideoProject",
    "TaskProgress",
    "VideoGroup",
    "ProjectStatus",
    "ProjectType",
    "ProjectMetadata",
    "ProjectSettings",
    "ProjectMedia",
    "ProjectTimeline",
]