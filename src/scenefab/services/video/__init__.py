"""
视频制作服务

保留的活跃模块：
- monologue_maker.py  第一人称解说视频制作（核心）
- base_maker.py        视频 Maker 基类

新增模块（架构升级）：
- perspective_mapper.py  第一人称视角映射器
- video_interleaver.py   视频穿插逻辑处理器

Phase 3 模块化拆分：
- cache/          视频帧缓存（LRU + 磁盘回退）
- session.py     FFmpeg 会话管理
- analyzer.py    视频分析器
- processor.py   视频处理器

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
from .models.monologue import EmotionType

from .perspective_mapper import PerspectiveMapper
from .video_interleaver import VideoInterleaver
from .models.perspective import (
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
from .extraction.first_person import (
    FirstPersonExtractor,
    VideoSegment,
)

from .extraction.emotion_peak import (
    EmotionPeakDetector,
    EmotionPeak,
)

# Phase 3 新增（Phase 4 重构至 selection/）
from .selection.seg_selector import (
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

from .highlight_detector import (
    HighlightDetector,
    HighlightSegment,
    HighlightReason,
    HighlightDetectorConfig,
)
from .pipeline_integrator import PipelineIntegrator
from .scene_converter import SceneConverter, EmotionCurveGenerator

# Phase 3 新增：视频处理模块
from .cache import VideoFrameCache
from .cache.legacy_cache import VideoCache
from .session import FFmpegSession
from .analyzer import VideoAnalyzer
from .processor import VideoProcessor

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
    # 高光检测
    "HighlightDetector",
    "HighlightSegment",
    "HighlightReason",
    "HighlightDetectorConfig",
    # 场景转换
    "SceneConverter",
    "EmotionCurveGenerator",
    # 流水线集成
    "PipelineIntegrator",
    # Phase 3 视频处理
    "VideoFrameCache",
    "VideoCache",
    "FFmpegSession",
    "VideoAnalyzer",
    "VideoProcessor",
]
