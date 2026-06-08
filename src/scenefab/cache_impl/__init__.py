#!/usr/bin/env python3

"""
缓存模块

提供多层缓存实现：
- MemoryCache: 内存LRU/LFU/FIFO缓存
- DiskCache: 磁盘持久化缓存
"""

from .disk_cache import DiskCache
from .memory_cache import MemoryCache


def calc_hit_rate(hit_count: int, miss_count: int) -> float:
    """计算缓存命中率"""
    total = hit_count + miss_count
    return hit_count / total if total > 0 else 0.0


__all__ = [
    "MemoryCache",
    "DiskCache",
    "calc_hit_rate",
]
