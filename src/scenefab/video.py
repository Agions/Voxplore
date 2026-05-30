"""
视频处理兼容层

此文件是向后兼容的适配层，原 video.py 中的功能已迁移至：
- services/video/cache/frame_cache.py - VideoFrameCache
- services/video/cache/legacy_cache.py - VideoCache (deprecated)
- services/video/session.py - FFmpegSession
- services/video/analyzer.py - VideoAnalyzer
- services/video/processor.py - VideoProcessor
"""
from __future__ import annotations

import warnings

# 检查导入路径以验证新模块可用性
try:
    from scenefab.services.video.cache.frame_cache import VideoFrameCache as _VFC
    from scenefab.services.video.cache.legacy_cache import VideoCache as _VC
    from scenefab.services.video.session import FFmpegSession as _FFS
    from scenefab.services.video.analyzer import VideoAnalyzer as _VA
    from scenefab.services.video.processor import VideoProcessor as _VP
    _SPLIT_AVAILABLE = True
except ImportError:
    _SPLIT_AVAILABLE = False
    _VFC = None
    _VC = None
    _FFS = None
    _VA = None
    _VP = None

warnings.warn(
    "scenefab.video is deprecated, import from scenefab.services.video instead",
    DeprecationWarning,
    stacklevel=2,
)

# 重新导出所有公共接口
if _SPLIT_AVAILABLE:
    VideoFrameCache = _VFC
    VideoCache = _VC
    FFmpegSession = _FFS
    VideoAnalyzer = _VA
    VideoProcessor = _VP
else:
    # 降级：如果拆分失败，至少保证导入不中断
    VideoFrameCache = None
    VideoCache = None
    FFmpegSession = None
    VideoAnalyzer = None
    VideoProcessor = None

__all__ = [
    "VideoFrameCache",
    "VideoCache",
    "FFmpegSession",
    "VideoAnalyzer",
    "VideoProcessor",
]