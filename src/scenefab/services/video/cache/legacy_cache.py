"""
视频帧缓存（兼容旧接口）

已废弃，请使用 VideoFrameCache。
此文件仅用于向后兼容。
"""
from __future__ import annotations

import warnings
from typing import Optional

import numpy as np

from .frame_cache import VideoFrameCache as _RealFrameCache

warnings.warn(
    "VideoCache is deprecated, use VideoFrameCache from services.video.cache instead",
    DeprecationWarning,
    stacklevel=2,
)


class VideoCache:
    """视频帧缓存（兼容旧接口，已废弃）"""

    # 全局共享缓存实例
    _shared_cache: Optional[_RealFrameCache] = None

    @classmethod
    def get_shared(cls) -> _RealFrameCache:
        """获取共享缓存实例"""
        if cls._shared_cache is None:
            cls._shared_cache = _RealFrameCache(
                max_frames=100,
                max_memory_mb=500,
                disk_fallback=True,
            )
        return cls._shared_cache

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache = {}  # type: ignore[var-annotated]
        self._access_order = []  # type: ignore[var-annotated]

    def get(self, key: str) -> np.ndarray | None:
        if key in self._cache:
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]  # type: ignore[no-any-return]
        return None

    def set(self, key: str, value: np.ndarray):
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self.max_size:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]

        self._cache[key] = value
        self._access_order.append(key)

    def clear(self):
        self._cache.clear()
        self._access_order.clear()


__all__ = ["VideoCache"]