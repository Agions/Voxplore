"""
视频制作服务

保留的活跃模块：
- monologue_maker.py  第一人称解说视频制作（核心）
- base_maker.py        视频 Maker 基类

新增模块（架构升级）：
- perspective_mapper.py  第一人称视角映射器
- video_interleaver.py   视频穿插逻辑处理器

Phase 4 模块化拆分：
- extraction/   第一人称提取、情感峰值检测
- selection/    片段选择策略
- grouping/     智能视频分组
"""

from .base_maker import BaseVideoMaker
from .monologue_maker import (
    MonologueMaker,
    MonologueProject,
    MonologueSegment,
    MonologueStyle,
)
from .models.monologue_models import EmotionType

from .perspective_mapper import PerspectiveMapper
from .video_interleaver import VideoInterleaver
from .models.perspective_models import (
    SceneSegment,
    KeyFrame,
    PerspectiveShot,
    NarrationSegment,
    ClipSegment,
    InterleaveTimeline,
    InterleaveDecision,
    InterleaveMode,
    TransitionType,
)

# Phase 3 新增（Phase 4 重构至 extraction/）
from .extraction.first_person_extractor import (
    FirstPersonExtractor,
    VideoSegment,
)

from .extraction.emotion_peak_detector import (
    EmotionPeakDetector,
    EmotionPeak,
)

# Phase 3 新增（Phase 4 重构至 selection/）
from .selection.segment_selector import (
    SegmentSelector,
    SelectionStrategy,
)

# Phase 3 新增（Phase 4 重构至 grouping/）
from .grouping.smart_grouper import (
    SmartGrouper,
    VideoGroup,
    VisionEmbedder,
    AudioEmbedder,
    GroupingReason,
)

__all__ = [
    # 原有
    "BaseVideoMaker",
    "MonologueMaker",
    "MonologueProject",
    "MonologueSegment",
    "MonologueStyle",
    "EmotionType",
    # 原有新增
    "PerspectiveMapper",
    "VideoInterleaver",
    "SceneSegment",
    "KeyFrame",
    "PerspectiveShot",
    "NarrationSegment",
    "ClipSegment",
    "InterleaveTimeline",
    "InterleaveDecision",
    "InterleaveMode",
    "TransitionType",
    # Phase 3 新增（extraction/）
    "FirstPersonExtractor",
    "VideoSegment",
    "EmotionPeakDetector",
    "EmotionPeak",
    # Phase 3 新增（selection/）
    "SegmentSelector",
    "SelectionStrategy",
    # Phase 3 新增（grouping/）
    "SmartGrouper",
    "VideoGroup",
    "VisionEmbedder",
    "AudioEmbedder",
    "GroupingReason",
]
