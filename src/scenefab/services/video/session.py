"""
FFmpeg 会话管理模块

复用 FFmpeg 进程避免重复启动开销。
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading

import numpy as np

from .cache.frame_cache import VideoFrameCache

logger = logging.getLogger(__name__)


class FFmpegSession:
    """
    FFmpeg 会话管理
    复用 FFmpeg 进程避免重复启动开销
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._processes = {}
        self._session_lock = threading.Lock()
        self._frame_cache = VideoFrameCache.get_shared()
        self._info_cache: dict[str, dict] = {}

    def get_video_info(self, video_path: str) -> dict:
        """使用 ffprobe 获取视频信息"""
        cache_key = f"info:{video_path}"

        # 尝试从缓存获取
        if cache_key in self._info_cache:
            return self._info_cache[cache_key]

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    video_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)

                video_stream = next(  # type: ignore[var-annotated]
                    (
                        s
                        for s in data.get("streams", [])
                        if s.get("codec_type") == "video"
                    ),
                    {},
                )

                format_info = data.get("format", {})

                from fractions import Fraction

                fps_str = video_stream.get("r_frame_rate", "30/1")
                if fps_str == "0/0":
                    fps = 30.0
                else:
                    fps = float(Fraction(fps_str))

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
        self, video_path: str, timestamps: list[float], progress_callback=None
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
                return self._extract_frames_decord(
                    video_path, timestamps, progress_callback
                )
        except ImportError:
            pass

        # 回退到 OpenCV
        return self._extract_frames_opencv(video_path, timestamps, progress_callback)

    def _extract_frames_decord(
        self, video_path: str, timestamps: list[float], progress_callback=None
    ) -> list[tuple[float, np.ndarray]]:
        """使用 decord 提取帧"""
        try:
            import cv2
            from decord import VideoReader, cpu

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
            return self._extract_frames_opencv(
                video_path, timestamps, progress_callback
            )

    def _extract_frames_opencv(
        self, video_path: str, timestamps: list[float], progress_callback=None
    ) -> list[tuple[float, np.ndarray]]:
        """使用 OpenCV 提取帧（回退方案）"""
        results = []  # type: ignore[var-annotated]

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

    def extract_audio(self, video_path: str, output_path: str = None) -> str | None:  # type: ignore[assignment]
        """提取音频"""
        if output_path is None:
            output_path = video_path.rsplit(".", 1)[0] + ".wav"  # type: ignore[unreachable]

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-vn",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    output_path,
                ],
                capture_output=True,
                timeout=300,
                check=True,
            )
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("Audio extraction timed out")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio extraction failed: {e}")
            return None


__all__ = ["FFmpegSession"]
