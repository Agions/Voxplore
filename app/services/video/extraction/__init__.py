"""视频提取服务模块

提取类服务：第一人称视角提取、情感峰值检测
"""

from .first_person_extractor import (
    VideoSegment,
    FirstPersonExtractor,
    VisionModel,
)

from .emotion_peak_detector import (
    EmotionPeak,
    EmotionPeakDetector,
)

__all__ = [
    "VideoSegment",
    "FirstPersonExtractor",
    "VisionModel",
    "EmotionPeak",
    "EmotionPeakDetector",
]
