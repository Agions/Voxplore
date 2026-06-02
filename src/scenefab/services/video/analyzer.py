"""
视频分析器模块

提供视频分析功能：信息获取、帧提取、场景检测、音频提取。
"""
from __future__ import annotations

import logging
from typing import Callable

import numpy as np

from .session import FFmpegSession

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """视频分析器"""

    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """获取视频信息"""
        session = FFmpegSession()
        return session.get_video_info(video_path)

    @staticmethod
    def extract_frame(video_path: str, timestamp: float) -> np.ndarray | None:
        """提取指定时间戳的帧"""
        session = FFmpegSession()
        return session.extract_frame(video_path, timestamp)

    @staticmethod
    def extract_frames_batch(
        video_path: str,
        timestamps: list[float],
        progress_callback: Callable | None = None
    ) -> list[tuple[float, np.ndarray]]:
        """批量提取帧"""
        session = FFmpegSession()
        return session.extract_frames_batch(video_path, timestamps, progress_callback)

    @staticmethod
    def detect_scenes(
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

    @staticmethod
    def extract_audio(video_path: str, output_path: str = None) -> str | None:
        """提取音频"""
        session = FFmpegSession()
        return session.extract_audio(video_path, output_path)


__all__ = ["VideoAnalyzer"]