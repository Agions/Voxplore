#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缓存管理器

实现统一的缓存系统，支持多种缓存策略。
提供内存缓存和磁盘缓存的统一访问接口。

模块结构:
- cache/memory_cache.py: MemoryCache 实现
- cache/disk_cache.py: DiskCache 实现
- cache_manager.py: CacheManager 统一管理
"""

import logging
from typing import Any, Optional, Dict
from threading import Lock

from .interfaces.cache_interface import CacheStats
from .cache_impl.memory_cache import MemoryCache
from .cache_impl.disk_cache import DiskCache


logger = logging.getLogger(__name__)


class CacheManager:
    """
    缓存管理器

    统一管理内存缓存和磁盘缓存。
    """

    _instance: Optional['CacheManager'] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._memory_cache = MemoryCache()
            self._disk_cache: Optional[DiskCache] = None
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'CacheManager':
        """获取实例"""
        return cls()

    def initialize_disk_cache(self, cache_dir: str, max_size_mb: int = 1000) -> None:
        """
        初始化磁盘缓存

        Args:
            cache_dir: 缓存目录
            max_size_mb: 最大大小
        """
        self._disk_cache = DiskCache(cache_dir, max_size_mb)

    def get(self, key: str, use_disk: bool = True) -> Optional[Any]:
        """
        获取缓存值

        先尝试内存缓存，再尝试磁盘缓存。

        Args:
            key: 缓存键
            use_disk: 是否使用磁盘缓存

        Returns:
            缓存值
        """
        # 先尝试内存缓存
        value = self._memory_cache.get(key)
        if value is not None:
            return value

        # 再尝试磁盘缓存
        if use_disk and self._disk_cache:
            value = self._disk_cache.get(key)
            if value is not None:
                # 回填到内存缓存
                self._memory_cache.set(key, value)
                return value

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            use_disk: bool = False, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间
            use_disk: 是否同时写入磁盘缓存
            metadata: 元数据

        Returns:
            是否设置成功
        """
        success = self._memory_cache.set(key, value, ttl, metadata)

        if success and use_disk and self._disk_cache:
            self._disk_cache.set(key, value, ttl, metadata)

        return success

    def delete(self, key: str) -> bool:
        """删除缓存"""
        memory_deleted = self._memory_cache.delete(key)
        disk_deleted = False
        if self._disk_cache:
            disk_deleted = self._disk_cache.delete(key)
        return memory_deleted or disk_deleted

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if self._memory_cache.exists(key):
            return True
        if self._disk_cache:
            return self._disk_cache.exists(key)
        return False

    def clear(self, clear_disk: bool = False) -> None:
        """清空缓存"""
        self._memory_cache.clear()
        if clear_disk and self._disk_cache:
            self._disk_cache.clear()

    def get_stats(self) -> Dict[str, CacheStats]:
        """获取缓存统计"""
        stats = {
            'memory': self._memory_cache.get_stats()
        }
        if self._disk_cache:
            stats['disk'] = self._disk_cache.get_stats()
        return stats

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        count = self._memory_cache.cleanup_expired()
        if self._disk_cache:
            count += self._disk_cache.cleanup_expired()
        return count

    def get_memory_cache(self) -> MemoryCache:
        """获取内存缓存"""
        return self._memory_cache

    def get_disk_cache(self) -> Optional[DiskCache]:
        """获取磁盘缓存"""
        return self._disk_cache


# 便捷函数
def get_cache_manager() -> CacheManager:
    """获取缓存管理器实例"""
    return CacheManager.get_instance()


def cached(ttl: Optional[int] = None, use_disk: bool = False):
    """
    缓存装饰器

    Args:
        ttl: 过期时间（秒）
        use_disk: 是否使用磁盘缓存
    """
    def decorator(func):
        cache_key = f"func:{func.__module__}.{func.__name__}"

        def wrapper(*args, **kwargs):
            key = f"{cache_key}:{str(args)}:{str(kwargs)}"
            manager = get_cache_manager()

            # 尝试获取缓存
            result = manager.get(key, use_disk)
            if result is not None:
                return result

            # 执行函数
            result = func(*args, **kwargs)

            # 缓存结果
            manager.set(key, result, ttl, use_disk)
            return result

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator



__all__ = [
    "CacheManager",
    "MemoryCache",
    "DiskCache",
    "get_cache_manager",
    "cached",
]
