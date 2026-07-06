"""视频制作服务。"""

from __future__ import annotations

from typing import Any

from scenefab.utils.lazy_imports import make_lazy_getattr

_EXPORTS = {
    "BaseVideoMaker": ".base_maker",
    "MonologueMaker": ".monologue_maker",
    "MonologueProject": ".monologue_maker",
    "MonologueSegment": ".monologue_maker",
    "MonologueStyle": ".monologue_maker",
    "EmotionType": ".models.monologue",
    "PerspectiveMapper": ".perspective_mapper",
    "VideoInterleaver": ".video_interleaver",
    "SceneSegment": ".models.perspective",
    "KeyFrame": ".models.perspective",
    "PerspectiveShot": ".models.perspective",
    "NarrationSegment": ".models.perspective",
    "ClipSegment": ".models.perspective",
    "InterleaveTimeline": ".models.perspective",
    "InterleaveDecision": ".models.perspective",
    "InterleaveMode": ".models.perspective",
    "TransitionType": ".models.perspective",
    "FirstPersonExtractor": ".extraction.first_person",
    "VideoSegment": ".extraction.first_person",
    "EmotionPeakDetector": ".extraction.emotion_peak",
    "EmotionPeak": ".extraction.emotion_peak",
    "SegmentSelector": ".selection.seg_selector",
    "SelectionStrategy": ".selection.seg_selector",
    "SmartGrouper": ".grouping.smart_grouper",
    "VideoGroup": ".grouping.smart_grouper",
    "VisionEmbedder": ".grouping.smart_grouper",
    "AudioEmbedder": ".grouping.smart_grouper",
    "GroupingReason": ".grouping.smart_grouper",
    "HighlightDetector": ".highlight_detector",
    "HighlightSegment": ".highlight_detector",
    "HighlightReason": ".highlight_detector",
    "HighlightDetectorConfig": ".highlight_detector",
    "SceneConverter": ".scene_converter",
    "EmotionCurveGenerator": ".scene_converter",
    "PipelineIntegrator": ".pipeline_integrator",
    "VideoFrameCache": ".cache",
    "FFmpegSession": ".session",
    "VideoAnalyzer": ".analyzer",
    "VideoProcessor": ".processor",
}


def __getattr__(name: str) -> Any:
    return _lazy_getattr(name)


_lazy_getattr = make_lazy_getattr(_EXPORTS, package_name=__name__)


__all__ = list(_EXPORTS)
