"""
视频制作服务

保留的活跃模块：
- monologue_maker.py  第一人称解说视频制作（核心）
- base_maker.py        视频 Maker 基类

新增模块（架构升级）：
- perspective_mapper.py  第一人称视角映射器
- video_interleaver.py   视频穿插逻辑处理器
"""

from .base_maker import BaseVideoMaker
from .monologue_maker import (
    MonologueMaker,
    MonologueProject,
    MonologueSegment,
    MonologueStyle,
)
from .models.monologue_models import EmotionType

# 新增：视角映射和穿插模块
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

__all__ = [
    # 原有
    "BaseVideoMaker",
    "MonologueMaker",
    "MonologueProject",
    "MonologueSegment",
    "MonologueStyle",
    "EmotionType",
    # 新增
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
]
