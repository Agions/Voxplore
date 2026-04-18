#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内存缓存实现 (MemoryCache)

基于 OrderedDict 实现 LRU/LFU/FIFO 缓存策略。
"""

import pickle
import logging
from typing import Any, Optional, Dict
from collections import OrderedDict
from datetime import datetime, timedelta
from threading import Lock

from app.core.interfaces.cache_interface import (
    ICache, CacheEntry, CacheStats, CachePolicy,
)


logger = logging.getLogger(__name__)


class MemoryCache(ICache):
    """
    内存缓存实现

    基于OrderedDict实现LRU缓存。
    """

    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100,
                 policy: CachePolicy = CachePolicy.LRU):
        """
        初始化内存缓存

        Args:
            max_size: 最大条目数
            max_memory_mb: 最大内存使用（MB）
            policy: 缓存策略
        """
        self._max_size = max_size
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._policy = policy
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()

        # 统计
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._miss_count += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._miss_count += 1
                return None

            # 更新访问信息
            entry.access_count += 1
            entry.last_accessed = datetime.now()

            # LRU策略：移动到末尾
            if self._policy == CachePolicy.LRU:
                self._cache.move_to_end(key)

            self._hit_count += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            metadata: 元数据

        Returns:
            是否设置成功
        """
        try:
            # 估算大小
            size_bytes = len(pickle.dumps(value))

            with self._lock:
                # 检查内存限制
                if size_bytes > self._max_memory_bytes:
                    return False

                # 计算过期时间
                expires_at = None
                if ttl:
                    expires_at = datetime.now() + timedelta(seconds=ttl)

                # 创建条目
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    expires_at=expires_at,
                    size_bytes=size_bytes,
                    metadata=metadata or {}
                )

                # 检查是否需要清理
                self._evict_if_needed(size_bytes)

                # 存储
                self._cache[key] = entry

                # LRU策略：移动到末尾
                if self._policy == CachePolicy.LRU:
                    self._cache.move_to_end(key)

                return True

        except Exception as e:
            logger.error(f"缓存设置失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._cache[key]
                return False
            return True

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> CacheStats:
        """
        获取缓存统计

        Returns:
            统计信息
        """
        with self._lock:
            total_size = sum(e.size_bytes for e in self._cache.values())
            total_requests = self._hit_count + self._miss_count
            hit_rate = self._hit_count / total_requests if total_requests > 0 else 0

            return CacheStats(
                total_entries=len(self._cache),
                total_size_bytes=total_size,
                hit_count=self._hit_count,
                miss_count=self._miss_count,
                eviction_count=self._eviction_count,
                hit_rate=hit_rate,
                avg_entry_size=total_size / len(self._cache) if self._cache else 0,
                max_size_bytes=self._max_memory_bytes,
                policy=self._policy
            )

    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """
        获取完整缓存条目

        Args:
            key: 缓存键

        Returns:
            缓存条目
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired:
                return entry
            return None

    def keys(self, pattern: Optional[str] = None) -> list[str]:
        """
        获取所有键

        Args:
            pattern: 匹配模式

        Returns:
            键列表
        """
        with self._lock:
            keys = list(self._cache.keys())

            if pattern:
                import fnmatch
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]

            return keys

    def cleanup_expired(self) -> int:
        """
        清理过期条目

        Returns:
            清理的条目数
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def _evict_if_needed(self, required_bytes: int) -> None:
        """
        如果需要则清理空间

        Args:
            required_bytes: 需要的字节数
        """
        current_size = sum(e.size_bytes for e in self._cache.values())

        while (len(self._cache) >= self._max_size or
               current_size + required_bytes > self._max_memory_bytes):

            if not self._cache:
                break

            # 根据策略选择淘汰项
            if self._policy == CachePolicy.LRU:
                # 移除最久未访问的
                key_to_remove = next(iter(self._cache))
            elif self._policy == CachePolicy.LFU:
                # 移除访问次数最少的
                key_to_remove = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].access_count
                )
            else:
                # 默认FIFO
                key_to_remove = next(iter(self._cache))

            entry = self._cache.pop(key_to_remove)
            current_size -= entry.size_bytes
            self._eviction_count += 1
