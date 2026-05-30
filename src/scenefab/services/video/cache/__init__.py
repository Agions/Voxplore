"""
视频缓存模块

包含：
- frame_cache.py: 高性能 LRU 帧缓存
- legacy_cache.py: 旧版 VideoCache 适配器（已废弃）
"""
from .frame_cache import VideoFrameCache

__all__ = ["VideoFrameCache"]