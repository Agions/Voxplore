"""
视频帧缓存模块

提供高性能 LRU 缓存，支持内存限制和磁盘回退。
"""
from __future__ import annotations

import logging
import os
import pickle
import shutil
import stat
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _safe_pickle_load(file_path: Path) -> Any:
    """安全加载 pickle 文件 - 检查文件权限防止篡改"""
    file_stat = file_path.stat()
    if file_stat.st_mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
        raise PermissionError(f"Cache file {file_path} has insecure permissions")
    if os.getuid() != file_stat.st_uid:
        raise PermissionError(f"Cache file {file_path} not owned by current user")
    with open(file_path, 'rb') as f:
        return pickle.load(f)


class VideoFrameCache:
    """
    视频帧 LRU 缓存，支持内存限制和磁盘回退

    特性：
    - LRU 淘汰策略
    - 最大帧数限制（max_frames=100）
    - 最大内存限制（max_memory_mb=500）
    - 磁盘回退：超限帧写入临时目录
    - 批量预提取关键帧支持

    使用示例：
        cache = VideoFrameCache.get_shared()

        # 存储帧
        cache.set("video_001@10.5", frame_array)

        # 获取帧（自动 LRU 更新）
        frame = cache.get("video_001@10.5")

        # 批量预提取
        cache.prefetch_batch("video_001", [0.0, 1.0, 2.0, ...], extract_func)

        # 获取缓存统计
        stats = cache.get_stats()
    """

    # 全局共享缓存实例
    _shared_cache: Optional["VideoFrameCache"] = None

    @classmethod
    def get_shared(cls) -> "VideoFrameCache":
        """获取共享缓存实例"""
        if cls._shared_cache is None:
            cls._shared_cache = cls(
                max_frames=100,
                max_memory_mb=500,
                disk_fallback=True,
            )
        return cls._shared_cache

    def __init__(
        self,
        max_frames: int = 100,
        max_memory_mb: int = 500,
        temp_dir: Optional[str] = None,
        disk_fallback: bool = True,
    ):
        """
        初始化视频帧缓存

        Args:
            max_frames: 最大缓存帧数
            max_memory_mb: 最大内存使用（MB）
            temp_dir: 临时目录路径（磁盘回退用）
            disk_fallback: 是否启用磁盘回退
        """
        self._max_frames = max_frames
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._disk_fallback = disk_fallback

        if temp_dir:
            self._disk_dir = Path(temp_dir)
        else:
            self._disk_dir = Path.home() / ".cache" / "scenefab" / "frames"
        self._disk_dir.mkdir(parents=True, exist_ok=True)

        self._memory_cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._memory_usage = 0

        self._lock = threading.Lock()

        # 统计
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0
        self._disk_write_count = 0
        self._disk_read_count = 0

    def _estimate_frame_size(self, frame: np.ndarray) -> int:
        """估算帧内存大小"""
        if frame is None:
            return 0
        return int(frame.nbytes)

    def _generate_key(self, video_path: str, timestamp: float) -> str:
        """生成缓存键"""
        return f"{video_path}@{timestamp:.3f}"

    def _get_disk_path(self, key: str) -> Path:
        """获取磁盘存储路径"""
        safe_key = key.replace("/", "_").replace(":", "_")
        return self._disk_dir / f"{safe_key}.pkl"

    def get(self, key: str) -> np.ndarray | None:
        """获取帧（自动 LRU 更新）"""
        with self._lock:
            if key in self._memory_cache:
                self._hit_count += 1
                self._memory_cache.move_to_end(key)
                return self._memory_cache[key]

            self._miss_count += 1

        # 尝试从磁盘读取
        if self._disk_fallback:
            disk_path = self._get_disk_path(key)
            if disk_path.exists():
                try:
                    frame = _safe_pickle_load(disk_path)
                    self._disk_read_count += 1
                    # 重新加入内存缓存
                    self.set(key, frame)
                    return frame
                except Exception as e:
                    logger.debug(f"磁盘读取失败: {e}")

        return None

    def set(self, key: str, frame: np.ndarray) -> bool:
        """存储帧"""
        if frame is None:
            return False

        frame_size = self._estimate_frame_size(frame)

        with self._lock:
            # 如果键已存在，先移除旧条目
            if key in self._memory_cache:
                old_frame = self._memory_cache.pop(key)
                self._memory_usage -= self._estimate_frame_size(old_frame)

            # 如果超出限制，淘汰旧帧
            while (
                len(self._memory_cache) >= self._max_frames
                or self._memory_usage + frame_size > self._max_memory_bytes
            ) and self._memory_cache:
                oldest_key, oldest_frame = self._memory_cache.popitem(last=False)
                evicted_size = self._estimate_frame_size(oldest_frame)
                self._memory_usage -= evicted_size
                self._eviction_count += 1

                # 磁盘回退：写入磁盘而不是删除
                if self._disk_fallback:
                    try:
                        disk_path = self._get_disk_path(oldest_key)
                        with open(disk_path, 'wb') as f:
                            pickle.dump(oldest_frame, f)
                        self._disk_write_count += 1
                    except Exception as e:
                        logger.debug(f"磁盘回退写入失败: {e}")

            # 存储到内存
            self._memory_cache[key] = frame
            self._memory_cache.move_to_end(key)
            self._memory_usage += frame_size

            return True

    def prefetch_batch(
        self,
        video_path: str,
        timestamps: list[float],
        extract_func: Callable[[str, float], Optional[np.ndarray]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict[str, np.ndarray]:
        """
        批量预提取关键帧（并行）

        Args:
            video_path: 视频路径
            timestamps: 时间戳列表
            extract_func: 提取函数，签名 (video_path, timestamp) -> np.ndarray
            progress_callback: 进度回调 (current, total)

        Returns:
            {缓存键: 帧数组} 字典
        """
        total = len(timestamps)

        # 第一步：并行提取所有缺失帧
        def extract_missing(ts: float) -> tuple[str, Optional[np.ndarray]]:
            key = self._generate_key(video_path, ts)
            # 检查缓存（只用于跳过，不阻塞其他线程）
            if self.get(key) is not None:
                return key, None
            frame = extract_func(video_path, ts)
            if frame is not None:
                return key, frame
            return key, None

        # 使用线程池并行提取，最多 max_workers 个并发
        max_workers = min(8, max(1, total))
        results = {}
        extracted_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(extract_missing, ts): ts for ts in timestamps}

            for i, future in enumerate(futures):
                key, frame = future.result()
                if frame is not None:
                    self.set(key, frame)
                    results[key] = frame
                    extracted_count += 1

                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(i + 1, total)

        return results

    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            return {
                "memory_frames": len(self._memory_cache),
                "memory_usage_mb": self._memory_usage / (1024 * 1024),
                "max_frames": self._max_frames,
                "max_memory_mb": self._max_memory_bytes / (1024 * 1024),
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "hit_rate": (
                    self._hit_count / (self._hit_count + self._miss_count)
                    if (self._hit_count + self._miss_count) > 0 else 0
                ),
                "eviction_count": self._eviction_count,
                "disk_write_count": self._disk_write_count,
                "disk_read_count": self._disk_read_count,
            }

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._memory_cache.clear()
            self._memory_usage = 0

            # 清理磁盘缓存
            if self._disk_dir.exists():
                shutil.rmtree(self._disk_dir)
                self._disk_dir.mkdir(parents=True, exist_ok=True)

    def clear_disk_cache(self) -> None:
        """只清理磁盘缓存"""
        if self._disk_dir.exists():
            shutil.rmtree(self._disk_dir)
            self._disk_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["VideoFrameCache"]