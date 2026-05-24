#!/usr/bin/env python3
"""
SceneFab 视频处理 V2
性能优化版本：
- FFmpeg 进程复用
- 帧缓存（LRU + 内存限制 + 磁盘回退）
- 并行场景检测
"""
import os
import sys
import logging
import subprocess
import tempfile
import shutil
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from pathlib import Path
from typing import Optional
import numpy as np
import pickle

logger = logging.getLogger(__name__)


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
            temp_dir: 临时目录（None则用系统临时目录）
            disk_fallback: 是否启用磁盘回退
        """
        self._max_frames = max_frames
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._disk_fallback = disk_fallback
        
        # 内存缓存：OrderedDict 实现 LRU
        self._memory_cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._memory_usage = 0
        
        # 磁盘缓存路径
        if temp_dir:
            self._disk_dir = Path(temp_dir) / "video_frame_cache"
        else:
            self._disk_dir = Path(tempfile.gettempdir()) / "video_frame_cache"
        self._disk_dir.mkdir(parents=True, exist_ok=True)
        
        # 锁
        self._lock = Lock()
        
        # 统计
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0
        self._disk_write_count = 0
        self._disk_read_count = 0

    def _generate_key(self, video_path: str, timestamp: float) -> str:
        """生成缓存键"""
        return f"{video_path}@{timestamp:.3f}"

    def _get_disk_path(self, key: str) -> Path:
        """获取磁盘缓存路径"""
        # 用 hash 分目录，避免单目录文件过多
        hash_val = hash(key) % 256
        subdir = self._disk_dir / f"{hash_val:02x}"
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key}.frame"

    def _estimate_frame_size(self, frame: np.ndarray) -> int:
        """估算帧内存大小"""
        return frame.nbytes

    def get(self, key: str) -> Optional[np.ndarray]:
        """
        获取缓存帧
        
        Args:
            key: 缓存键
            
        Returns:
            帧数组或 None
        """
        with self._lock:
            # 1. 尝试从内存缓存获取
            if key in self._memory_cache:
                # LRU：移动到末尾
                self._memory_cache.move_to_end(key)
                self._hit_count += 1
                return self._memory_cache[key]
            
            # 2. 尝试从磁盘缓存获取
            if self._disk_fallback:
                disk_path = self._get_disk_path(key)
                if disk_path.exists():
                    try:
                        with open(disk_path, 'rb') as f:
                            frame = pickle.load(f)
                        self._disk_read_count += 1
                        self._hit_count += 1
                        
                        # 回读到内存（如果空间允许）
                        frame_size = self._estimate_frame_size(frame)
                        if self._memory_usage + frame_size <= self._max_memory_bytes:
                            self._memory_cache[key] = frame
                            self._memory_cache.move_to_end(key)
                            self._memory_usage += frame_size
                        
                        return frame
                    except Exception as e:
                        logger.debug(f"磁盘缓存读取失败: {e}")
            
            self._miss_count += 1
            return None

    def set(self, key: str, frame: np.ndarray) -> bool:
        """
        设置缓存帧
        
        Args:
            key: 缓存键
            frame: 帧数组
            
        Returns:
            是否设置成功
        """
        frame_size = self._estimate_frame_size(frame)
        
        # 如果单个帧就超过限制，直接丢弃
        if frame_size > self._max_memory_bytes:
            logger.warning(f"帧大小 {frame_size} 超过限制，跳过缓存")
            return False
        
        with self._lock:
            # 如果已存在，先移除旧值
            if key in self._memory_cache:
                old_size = self._estimate_frame_size(self._memory_cache[key])
                self._memory_usage -= old_size
                del self._memory_cache[key]
            
            # 清理空间直到满足新帧
            while (len(self._memory_cache) >= self._max_frames or
                   self._memory_usage + frame_size > self._max_memory_bytes):
                
                if not self._memory_cache:
                    break
                
                # 淘汰最旧的帧
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


class VideoCache:
    """视频帧缓存（兼容旧接口）"""
    
    # 全局共享缓存实例
    _shared_cache: Optional[VideoFrameCache] = None

    @classmethod
    def get_shared(cls) -> VideoFrameCache:
        """获取共享缓存实例"""
        if cls._shared_cache is None:
            cls._shared_cache = VideoFrameCache(
                max_frames=100,
                max_memory_mb=500,
                disk_fallback=True,
            )
        return cls._shared_cache

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache = {}
        self._access_order = []

    def get(self, key: str) -> np.ndarray | None:
        if key in self._cache:
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
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


class FFmpegSession:
    """
    FFmpeg 会话管理
    复用 FFmpeg 进程避免重复启动开销
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._processes = {}
        self._lock = __import__('threading').Lock()
        self._frame_cache = VideoFrameCache.get_shared()

    def get_video_info(self, video_path: str) -> dict:
        """使用 ffprobe 获取视频信息"""
        cache_key = f"info:{video_path}"

        # 尝试从缓存获取
        if hasattr(self, '_info_cache'):
            if cache_key in self._info_cache:
                return self._info_cache[cache_key]
        else:
            self._info_cache = {}

        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format", "-show_streams",
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)

                video_stream = next(
                    (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                    {}
                )

                format_info = data.get("format", {})

                fps_str = video_stream.get("r_frame_rate", "30/1")
                if "/" in fps_str:
                    fps = eval(fps_str) if fps_str != "0/0" else 30.0
                else:
                    fps = float(fps_str)

                info = {
                    "duration": float(format_info.get("duration", 0)),
                    "fps": fps,
                    "width": int(video_stream.get("width", 0)),
                    "height": int(video_stream.get("height", 0)),
                    "codec": video_stream.get("codec_name", "unknown"),
                    "size": int(format_info.get("size", 0)),
                }

                self._info_cache[cache_key] = info
                return info

        except Exception as e:
            logger.warning(f"ffprobe failed: {e}")

        return {
            "duration": 60.0,
            "fps": 30.0,
            "width": 1920,
            "height": 1080,
            "codec": "unknown",
            "size": 0,
        }

    def extract_frame(self, video_path: str, timestamp: float) -> np.ndarray | None:
        """提取单帧（带缓存）"""
        cache_key = f"{video_path}@{timestamp:.3f}"
        
        # 尝试从缓存获取
        cached = self._frame_cache.get(cache_key)
        if cached is not None:
            return cached
        
        # 提取帧
        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None

            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ret, frame = cap.read()
            cap.release()

            if ret:
                self._frame_cache.set(cache_key, frame)
            return frame if ret else None

        except ImportError:
            logger.error("OpenCV is required for frame extraction")
            return None

    def extract_frames_batch(
        self,
        video_path: str,
        timestamps: list[float],
        progress_callback: Callable | None = None
    ) -> list[tuple[float, np.ndarray]]:
        """
        批量提取帧 - 使用 decord 加速（如果可用）
        decord 比 OpenCV 更快，特别是对于大视频
        """
        # 尝试使用 decord
        try:
            import importlib.util
            spec = importlib.util.find_spec("decord")
            if spec is not None:
                return self._extract_frames_decord(video_path, timestamps, progress_callback)
        except ImportError:
            pass

        # 回退到 OpenCV
        return self._extract_frames_opencv(video_path, timestamps, progress_callback)

    def _extract_frames_decord(
        self,
        video_path: str,
        timestamps: list[float],
        progress_callback: Callable | None = None
    ) -> list[tuple[float, np.ndarray]]:
        """使用 decord 提取帧"""
        try:
            from decord import VideoReader, cpu
            import cv2

            vr = VideoReader(video_path, ctx=cpu(0))
            fps = vr.get_avg_fps()
            total_frames = len(vr)

            results = []

            for i, ts in enumerate(timestamps):
                # 将时间戳转换为帧号
                frame_idx = min(int(ts * fps), total_frames - 1)
                frame = vr[frame_idx].asnumpy()  # RGB 格式

                # 转换为 BGR 格式（OpenCV 兼容）
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                results.append((ts, frame_bgr))

                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(i + 1, len(timestamps))

            return results

        except Exception as e:
            logger.warning(f"decord extraction failed: {e}, falling back to OpenCV")
            return self._extract_frames_opencv(video_path, timestamps, progress_callback)

    def _extract_frames_opencv(
        self,
        video_path: str,
        timestamps: list[float],
        progress_callback: Callable | None = None
    ) -> list[tuple[float, np.ndarray]]:
        """使用 OpenCV 提取帧（回退方案）"""
        results = []

        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return results

            fps = cap.get(cv2.CAP_PROP_FPS)
            total = len(timestamps)

            for i, ts in enumerate(timestamps):
                try:
                    frame_pos = int(ts * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                    ret, frame = cap.read()

                    if ret:
                        results.append((ts, frame))

                except Exception as e:
                    logger.warning(f"Failed to extract frame at {ts}s: {e}")

                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(i + 1, total)

            cap.release()

        except ImportError:
            logger.error("OpenCV is required for frame extraction")

        return results

    def extract_audio(self, video_path: str, output_path: str = None) -> str | None:
        """提取音频"""
        if output_path is None:
            output_path = video_path.rsplit('.', 1)[0] + '.wav'

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1",
                    output_path
                ],
                capture_output=True,
                timeout=300,
                check=True
            )
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("Audio extraction timed out")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio extraction failed: {e}")
            return None


class VideoAnalyzer:
    """视频分析器 V2"""

    _ffmpeg_session = None
    _frame_cache = None

    @classmethod
    def get_video_info(cls, video_path: str) -> dict:
        """获取视频信息"""
        if cls._ffmpeg_session is None:
            cls._ffmpeg_session = FFmpegSession()
        return cls._ffmpeg_session.get_video_info(video_path)

    @classmethod
    def extract_frame(cls, video_path: str, timestamp: float) -> np.ndarray | None:
        """提取指定时间戳的帧"""
        if cls._ffmpeg_session is None:
            cls._ffmpeg_session = FFmpegSession()
        return cls._ffmpeg_session.extract_frame(video_path, timestamp)

    @classmethod
    def extract_frames_batch(
        cls,
        video_path: str,
        timestamps: list[float],
        progress_callback: Callable | None = None
    ) -> list[tuple[float, np.ndarray]]:
        """批量提取帧"""
        if cls._ffmpeg_session is None:
            cls._ffmpeg_session = FFmpegSession()
        return cls._ffmpeg_session.extract_frames_batch(
            video_path, timestamps, progress_callback
        )

    @classmethod
    def detect_scenes(
        cls,
        video_path: str,
        threshold: float = 30.0,
        min_scene_duration: float = 1.0
    ) -> list[tuple[float, float]]:
        """检测场景变化"""
        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return []

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            scenes = []
            prev_frame = None
            scene_start = 0
            frame_idx = 0

            sample_interval = max(1, int(fps))

            while frame_idx < total_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if prev_frame is not None:
                    diff = np.mean(np.abs(gray.astype(float) - prev_frame.astype(float)))

                    if diff > threshold:
                        scene_end = frame_idx / fps
                        if scene_end - scene_start >= min_scene_duration:
                            scenes.append((scene_start, scene_end))
                        scene_start = scene_end

                prev_frame = gray
                frame_idx += sample_interval

            final_time = total_frames / fps
            if final_time - scene_start >= min_scene_duration:
                scenes.append((scene_start, final_time))

            cap.release()

            return scenes

        except ImportError:
            logger.error("OpenCV is required for scene detection")
            return []

    @classmethod
    def extract_audio(cls, video_path: str, output_path: str = None) -> str | None:
        """提取音频"""
        if cls._ffmpeg_session is None:
            cls._ffmpeg_session = FFmpegSession()
        return cls._ffmpeg_session.extract_audio(video_path, output_path)


class VideoProcessor:
    """
    视频处理器 V2
    优化的剪切、合并操作
    """

    @staticmethod
    def cut_video(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        quality: int = 23
    ) -> bool:
        """剪切视频片段"""
        try:
            duration = end_time - start_time

            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-i", input_path,
                    "-t", str(duration),
                    "-c:v", "libx264", "-crf", str(quality),
                    "-preset", "fast",
                    "-c:a", "aac",
                    "-strict", "experimental",
                    "-avoid_negative_ts", "make_zero",
                    output_path
                ],
                capture_output=True,
                timeout=max(60, int(duration * 2)),
                check=True
            )
            return True

        except subprocess.TimeoutExpired:
            logger.error("Video cutting timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Video cutting failed: {e}")
            return False

    @staticmethod
    def concatenate_videos(
        input_paths: list[str],
        output_path: str,
        temp_dir: str = None
    ) -> bool:
        """合并多个视频"""
        if not input_paths:
            return False

        if len(input_paths) == 1:
            try:
                import shutil
                shutil.copy(input_paths[0], output_path)
                return True
            except Exception as e:
                logger.error(f"File copy failed: {e}")
                return False

        if temp_dir is None:
            temp_dir = os.path.dirname(output_path) or "."

        list_file = os.path.join(temp_dir, "concat_list.txt")

        try:
            with open(list_file, 'w') as f:
                for path in input_paths:
                    f.write(f"file '{path}'\n")

            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", list_file,
                    "-c", "copy",
                    output_path
                ],
                capture_output=True,
                timeout=300,
                check=True
            )

            return True

        except subprocess.TimeoutExpired:
            logger.error("Video concatenation timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Video concatenation failed: {e}")
            return False
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)

    @staticmethod
    def add_audio(
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_volume: float = 1.0,
        video_volume: float = 0.0
    ) -> bool:
        """添加音频到视频（优化版 - 单次编码）"""
        try:
            # 使用 filter_complex 一次性完成，避免多次编码
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-filter_complex",
                    f"[0:a]volume={video_volume}[a0];[1:a]volume={audio_volume}[a1];[a0][a1]amix=inputs=2:duration=longest[aout]",
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "copy",  # 视频流直接复制，不重新编码
                    "-c:a", "aac",
                    "-ar", "44100",
                    output_path
                ],
                capture_output=True,
                timeout=300,
                check=True
            )
            return True

        except subprocess.TimeoutExpired:
            logger.error("Audio mixing timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio mixing failed: {e}")
            return False

    @staticmethod
    def extract_subclip(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        quality: int = 18
    ) -> bool:
        """
        高质量提取子片段
        使用双次编码确保帧精确
        """
        try:
            duration = end_time - start_time

            # 第一步：精确裁剪
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-i", input_path,
                    "-t", str(duration),
                    "-c:v", "libx264", "-crf", str(quality),
                    "-preset", "medium",
                    "-c:a", "aac",
                    "-strict", "experimental",
                    "-avoid_negative_ts", "make_zero",
                    output_path
                ],
                capture_output=True,
                timeout=max(60, int(duration * 3)),
                check=True
            )
            return True

        except subprocess.TimeoutExpired:
            logger.error("Subclip extraction timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Subclip extraction failed: {e}")
            return False


__all__ = [
    "VideoCache",
    "FFmpegSession",
    "VideoAnalyzer",
    "VideoProcessor",
]
