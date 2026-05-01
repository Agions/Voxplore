#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
磁盘缓存实现 (DiskCache)

将缓存持久化到磁盘，支持过期清理和LRU淘汰。
"""

import pickle
import json
import logging
from typing import Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock

from app.core.interfaces.cache_interface import (
    ICache, CacheEntry, CacheStats, CachePolicy,
)


logger = logging.getLogger(__name__)


class DiskCache(ICache):
    """
    磁盘缓存实现

    将缓存持久化到磁盘。
    """

    def __init__(self, cache_dir: str, max_size_mb: int = 1000):
        """
        初始化磁盘缓存

        Args:
            cache_dir: 缓存目录
            max_size_mb: 最大缓存大小（MB）
        """
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = Lock()

        # 统计
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用两层目录结构避免单个目录文件过多
        hash_val = hash(key) % 256
        subdir = self._cache_dir / f"{hash_val:02x}"
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key}.cache"

    def _get_metadata_path(self, cache_path: Path) -> Path:
        """获取元数据文件路径"""
        return cache_path.with_suffix('.meta')

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(cache_path)

        if not cache_path.exists() or not meta_path.exists():
            self._miss_count += 1
            return None

        try:
            # 读取元数据
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            # 检查过期
            expires_at = metadata.get('expires_at')
            if expires_at:
                expires = datetime.fromisoformat(expires_at)
                if datetime.now() > expires:
                    self._delete_files(cache_path, meta_path)
                    self._miss_count += 1
                    return None

            # 读取缓存值
            with open(cache_path, 'rb') as f:
                value = pickle.load(f)

            # 更新访问次数
            metadata['access_count'] = metadata.get('access_count', 0) + 1
            metadata['last_accessed'] = datetime.now().isoformat()
            with open(meta_path, 'w') as f:
                json.dump(metadata, f)

            self._hit_count += 1
            return value

        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            self._miss_count += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            metadata: Optional[dict] = None) -> bool:
        """设置缓存值"""
        try:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(cache_path)

            # 序列化值
            data = pickle.dumps(value)
            size_bytes = len(data)

            # 检查并清理空间
            self._evict_if_needed(size_bytes)

            # 写入缓存文件
            with open(cache_path, 'wb') as f:
                f.write(data)

            # 写入元数据
            meta = {
                'key': key,
                'created_at': datetime.now().isoformat(),
                'size_bytes': size_bytes,
                'access_count': 0,
                'metadata': metadata or {}
            }

            if ttl:
                meta['expires_at'] = (datetime.now() + timedelta(seconds=ttl)).isoformat()

            with open(meta_path, 'w') as f:
                json.dump(meta, f)

            return True

        except Exception as e:
            logger.error(f"写入缓存失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(cache_path)

        if cache_path.exists():
            self._delete_files(cache_path, meta_path)
            return True
        return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(cache_path)

        if not cache_path.exists() or not meta_path.exists():
            return False

        # 检查过期
        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            expires_at = metadata.get('expires_at')
            if expires_at:
                expires = datetime.fromisoformat(expires_at)
                if datetime.now() > expires:
                    self._delete_files(cache_path, meta_path)
                    return False

            return True
        except json.JSONDecodeError:
            return False  # 损坏的元数据视为过期
        except Exception as e:
            logger.warning(f"Cache expiry check failed: {e}")
            return False

    def clear(self) -> None:
        """清空缓存"""
        if self._cache_dir.exists():
            import shutil
            shutil.rmtree(self._cache_dir)
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        total_size = 0
        total_entries = 0

        for cache_file in self._cache_dir.rglob('*.cache'):
            total_size += cache_file.stat().st_size
            total_entries += 1

        total_requests = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total_requests if total_requests > 0 else 0

        return CacheStats(
            total_entries=total_entries,
            total_size_bytes=total_size,
            hit_count=self._hit_count,
            miss_count=self._miss_count,
            eviction_count=self._eviction_count,
            hit_rate=hit_rate,
            avg_entry_size=total_size / total_entries if total_entries > 0 else 0,
            max_size_bytes=self._max_size_bytes,
            policy=CachePolicy.LRU
        )

    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """获取完整缓存条目"""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(cache_path)

        if not meta_path.exists():
            return None

        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            expires_at = metadata.get('expires_at')
            if expires_at:
                expires = datetime.fromisoformat(expires_at)
                if datetime.now() > expires:
                    return None

            return CacheEntry(
                key=key,
                value=None,  # 不加载值
                created_at=datetime.fromisoformat(metadata['created_at']),
                expires_at=expires,
                access_count=metadata.get('access_count', 0),
                last_accessed=datetime.fromisoformat(metadata.get('last_accessed', metadata['created_at'])),
                size_bytes=metadata['size_bytes'],
                metadata=metadata.get('metadata', {})
            )
        except json.JSONDecodeError:
            return None
        except Exception as e:
            logger.warning(f"Failed to load cache entry for key {key!r}: {e}")
            return None

    def keys(self, pattern: Optional[str] = None) -> list[str]:
        """获取所有键"""
        keys = []
        for meta_file in self._cache_dir.rglob('*.meta'):
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                key = metadata.get('key')
                if key:
                    if pattern is None:
                        keys.append(key)
                    else:
                        import fnmatch
                        if fnmatch.fnmatch(key, pattern):
                            keys.append(key)
            except Exception as e:
                logger.debug(f"Cache keys iteration error: {e}")
        return keys

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        count = 0
        for meta_file in list(self._cache_dir.rglob('*.meta')):
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)

                expires_at = metadata.get('expires_at')
                if expires_at:
                    expires = datetime.fromisoformat(expires_at)
                    if datetime.now() > expires:
                        cache_path = meta_file.with_suffix('.cache')
                        self._delete_files(cache_path, meta_file)
                        count += 1
            except Exception as e:
                logger.debug(f"Cleanup iteration error: {e}")
        return count

    def _delete_files(self, cache_path: Path, meta_path: Path) -> None:
        """删除缓存文件"""
        try:
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
        except Exception as e:
            logger.debug(f"Delete cache files error: {e}")

    def _evict_if_needed(self, required_bytes: int) -> None:
        """如果需要则清理空间"""
        current_size = sum(
            f.stat().st_size
            for f in self._cache_dir.rglob('*')
            if f.is_file()
        )

        while current_size + required_bytes > self._max_size_bytes:
            # 找到最旧的文件
            oldest_file = None
            oldest_time = None

            for meta_file in self._cache_dir.rglob('*.meta'):
                try:
                    mtime = meta_file.stat().st_mtime
                    if oldest_time is None or mtime < oldest_time:
                        oldest_time = mtime
                        oldest_file = meta_file
                except Exception as e:
                    logger.debug(f"Stat cache file error: {e}")

            if oldest_file is None:
                break

            cache_path = oldest_file.with_suffix('.cache')
            self._delete_files(cache_path, oldest_file)

            if cache_path.exists():
                current_size -= cache_path.stat().st_size

            self._eviction_count += 1
