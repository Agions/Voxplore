"""
SceneFab 帧提取与视觉分析混入

提供视频帧提取、视觉显著性评分和封面选择等方法。
"""

import logging
from typing import Any

from scenefab.services.cover.models import HighlightFrame

logger = logging.getLogger(__name__)


class FrameUtilsMixin:
    """帧提取与视觉分析混入类"""

    def _extract_highlight_frames(
        self,
        video_path: str,
        emotion_data: list[dict[str, Any]] | None,
        num_frames: int,
    ) -> list[HighlightFrame]:
        """
        提取高光帧

        Args:
            video_path: 视频文件路径
            emotion_data: 情绪数据
            num_frames: 帧数量

        Returns:
            list: 高光帧列表
        """
        highlight_frames = []

        # 基于情绪数据提取高光时刻
        if emotion_data:
            # 按情绪强度排序
            sorted_emotions = sorted(
                emotion_data,
                key=lambda x: x.get("intensity", 0),
                reverse=True,
            )

            # 取前 N 个高光时刻
            for emotion in sorted_emotions[:num_frames]:
                timestamp = emotion.get("timestamp", 0)
                intensity = emotion.get("intensity", 0)

                # 提取帧
                frame_path = self._extract_frame(video_path, timestamp)

                highlight_frames.append(HighlightFrame(
                    timestamp=timestamp,
                    frame_path=frame_path,
                    emotion_score=intensity,
                    combined_score=intensity,
                ))
        else:
            # 如果没有情绪数据，均匀采样
            duration = self._get_video_duration(video_path)
            interval = duration / (num_frames + 1)

            for i in range(num_frames):
                timestamp = interval * (i + 1)
                frame_path = self._extract_frame(video_path, timestamp)

                highlight_frames.append(HighlightFrame(
                    timestamp=timestamp,
                    frame_path=frame_path,
                    visual_score=0.5,
                    emotion_score=0.5,
                    combined_score=0.5,
                ))

        # 计算视觉显著性分数
        for frame in highlight_frames:
            if frame.frame_path:
                frame.visual_score = self._calculate_visual_score(frame.frame_path)
                frame.combined_score = (
                    frame.visual_score * 0.5 + frame.emotion_score * 0.5
                )

        # 按综合分数排序
        highlight_frames.sort(key=lambda x: x.combined_score, reverse=True)

        return highlight_frames

    def _extract_frame(self, video_path: str, timestamp: float) -> str:
        """
        提取视频帧

        Args:
            video_path: 视频文件路径
            timestamp: 时间戳（秒）

        Returns:
            str: 帧图片路径
        """
        try:
            import subprocess
            from pathlib import Path

            output_path = str(Path(video_path).parent / f"frame_{timestamp:.2f}.jpg")

            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(timestamp),
                "-vframes", "1",
                "-y",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)

            return output_path

        except Exception as e:
            logger.warning(f"帧提取失败: {e}")
            return ""

    def _calculate_visual_score(self, frame_path: str) -> float:
        """
        计算视觉显著性分数

        Args:
            frame_path: 帧图片路径

        Returns:
            float: 视觉分数 0.0-1.0
        """
        try:
            import cv2
            import numpy as np

            # 读取图片
            img = cv2.imread(frame_path)
            if img is None:
                return 0.5

            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 计算多个视觉特征
            brightness = np.mean(gray) / 255.0
            contrast = np.std(gray) / 255.0

            # 计算边缘密度（使用 Canny 边缘检测）
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.sum(edges > 0) / edges.size

            # 计算颜色丰富度
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            color_richness = np.std(hsv[:, :, 0]) / 180.0

            # 综合分数
            visual_score = (
                brightness * 0.2
                + contrast * 0.3
                + edge_density * 0.3
                + color_richness * 0.2
            )

            return min(1.0, visual_score)

        except Exception as e:
            logger.warning(f"视觉分数计算失败: {e}")
            return 0.5

    def _select_best_cover(
        self,
        highlight_frames: list[HighlightFrame],
    ) -> HighlightFrame | None:
        """
        选择最佳封面

        Args:
            highlight_frames: 高光帧列表

        Returns:
            HighlightFrame: 最佳封面
        """
        if not highlight_frames:
            return None

        # 选择综合分数最高的帧
        return max(highlight_frames, key=lambda x: x.combined_score)

    def _get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            float: 视频时长（秒）
        """
        try:
            import subprocess
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"获取视频时长失败: {e}")
            return 0.0
