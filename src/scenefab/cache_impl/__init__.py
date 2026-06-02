#!/usr/bin/env python3

"""
缓存模块

提供多层缓存实现：
- MemoryCache: 内存LRU/LFU/FIFO缓存
- DiskCache: 磁盘持久化缓存
"""

from .disk_cache import DiskCache
from .memory_cache import MemoryCache

__all__ = [
    "MemoryCache",
    "DiskCache",
]
