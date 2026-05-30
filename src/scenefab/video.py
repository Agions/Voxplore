"""
视频处理模块（兼容层）

已迁移至 scenefab.services.video
"""
from scenefab.services.video.cache.frame_cache import VideoFrameCache
from scenefab.services.video.cache.legacy_cache import VideoCache
from scenefab.services.video.session import FFmpegSession
from scenefab.services.video.analyzer import VideoAnalyzer
from scenefab.services.video.processor import VideoProcessor

__all__ = [
    "VideoFrameCache",
    "VideoCache",
    "FFmpegSession",
    "VideoAnalyzer",
    "VideoProcessor",
]