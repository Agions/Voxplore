"""视频提取服务模块

提取类服务：第一人称视角提取、情感峰值检测
"""

from .emotion_peak import (
    EmotionPeak,
    EmotionPeakDetector,
)
from .first_person import (
    FirstPersonExtractor,
    VideoSegment,
    VisionModel,
)

__all__ = [
    "VideoSegment",
    "FirstPersonExtractor",
    "VisionModel",
    "EmotionPeak",
    "EmotionPeakDetector",
]
