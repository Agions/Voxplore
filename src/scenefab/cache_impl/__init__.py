#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缓存模块

提供多层缓存实现：
- MemoryCache: 内存LRU/LFU/FIFO缓存
- DiskCache: 磁盘持久化缓存
"""

from .memory_cache import MemoryCache
from .disk_cache import DiskCache


__all__ = [
    "MemoryCache",
    "DiskCache",
]
