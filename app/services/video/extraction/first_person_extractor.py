#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FirstPersonExtractor - 第一人称视角提取服务

功能：
1. 逐帧分析画面（采样每 N 帧）
2. Qwen2.5-VL 判断"我"的主体视角
3. 提取适合做解说的片段（时序连续、信息完整）
4. 返回片段列表（含时间戳、置信度）

接口预留：
- 视觉模型: VisionModel 协议（未来替换为真实 Qwen2.5-VL）
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
import numpy as np


@dataclass
class VideoSegment:
    """视频片段"""
    video_path: str
    start_time: float  # 秒
    end_time: float    # 秒
    confidence: float  # 0.0 ~ 1.0，第一人称置信度
    description: str   # 片段描述


@runtime_checkable
class VisionModel(Protocol):
    """视觉模型协议

    实现此协议以接入真实 Qwen2.5-VL 模型
    """

    def analyze_frame(self, video_path: str, timestamp: float) -> dict:
        """分析单帧

        Args:
            video_path: 视频路径
            timestamp: 时间戳（秒）

        Returns:
            {
                "is_first_person": bool,
                "confidence": float,  # 0.0 ~ 1.0
                "description": str,
            }
        """
        ...


class MockVisionModel:
    """模拟视觉模型（用于测试和开发）"""

    def __init__(self, seed: int = 42):
        self._rng = np.random.RandomState(seed)

    def analyze_frame(self, video_path: str, timestamp: float) -> dict:
        # 模拟：基于时间戳生成一些第一人称区域
        # 实际使用时会被真实模型替换
        hash_val = hash(video_path + f"_{timestamp:.1f}") % (2**31)
        rng = np.random.RandomState(hash_val)

        # 模拟判断（实际应接入真实视觉模型）
        # 这里简单模拟：30% 概率是第一人称，低置信度
        if rng.rand() < 0.3:
            return {
                "is_first_person": True,
                "confidence": 0.5 + rng.rand() * 0.4,
                "description": f"第一人称视角 @{timestamp:.1f}s",
            }
        else:
            return {
                "is_first_person": False,
                "confidence": rng.rand() * 0.4,
                "description": "",
            }


class FirstPersonExtractor:
    """第一人称视角提取器"""

    # 帧采样间隔（秒）
    DEFAULT_FRAME_INTERVAL = 1.0

    # 最短片段时长（秒）
    MIN_SEGMENT_DURATION = 9.0

    # 最长片段时长（秒）
    MAX_SEGMENT_DURATION = 60.0

    # 最小置信度阈值
    MIN_CONFIDENCE_THRESHOLD = 0.6

    def __init__(
        self,
        vision_model: VisionModel | None = None,
        frame_interval: float = DEFAULT_FRAME_INTERVAL,
        min_confidence: float = MIN_CONFIDENCE_THRESHOLD,
    ):
        """初始化提取器

        Args:
            vision_model: 视觉模型（默认使用 Mock）
            frame_interval: 帧采样间隔（秒）
            min_confidence: 最小置信度阈值
        """
        self._vision_model = vision_model or MockVisionModel()
        self._frame_interval = frame_interval
        self._min_confidence = min_confidence

    def extract_first_person_segments(
        self,
        video_path: str,
        group_id: str = "",
    ) -> list[VideoSegment]:
        """提取第一人称片段

        Args:
            video_path: 视频路径
            group_id: 分组 ID（用于未来多视频联合分析）

        Returns:
            第一人称片段列表（按置信度降序排列）
        """
        # 获取视频时长（模拟，实际应调用 ffprobe）
        duration = self._get_video_duration(video_path)

        if duration <= 0:
            return []

        # 逐帧分析
        frame_results = []
        timestamp = 0.0
        frame_errors = 0
        while timestamp < duration:
            try:
                result = self._vision_model.analyze_frame(video_path, timestamp)
                frame_results.append((timestamp, result))
            except Exception as e:
                frame_errors += 1
                frame_results.append((timestamp, {
                    "is_first_person": False,
                    "confidence": 0.0,
                    "description": "",
                }))
            timestamp += self._frame_interval

        if frame_errors > 0:
            logger.warning(f"Frame analysis errors: {frame_errors}/{int(duration / self._frame_interval) + 1}")

        # 聚类连续的第一人称帧
        segments = self._cluster_segments(frame_results, video_path)

        # 过滤和整理
        filtered_segments = self._filter_segments(segments)

        # 按置信度排序
        filtered_segments.sort(key=lambda s: s.confidence, reverse=True)

        return filtered_segments

    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长（秒）

        实际实现应调用 ffprobe
        这里使用模拟值
        """
        # 模拟：默认 60 秒视频
        # 未来接入真实 ffprobe
        return 60.0

    def _cluster_segments(
        self,
        frame_results: list[tuple[float, dict]],
        video_path: str,
    ) -> list[VideoSegment]:
        """将连续的第一人称帧聚类成片段"""
        segments = []
        current_start = None
        current_end = None
        current_confidences = []
        current_descriptions = []

        for timestamp, result in frame_results:
            if result["is_first_person"] and result["confidence"] >= self._min_confidence:
                if current_start is None:
                    current_start = timestamp
                    current_end = timestamp
                    current_confidences = []
                    current_descriptions = []

                current_end = timestamp
                current_confidences.append(result["confidence"])
                if result["description"]:
                    current_descriptions.append(result["description"])
            else:
                if current_start is not None:
                    # 完成当前片段
                    avg_conf = np.mean(current_confidences) if current_confidences else 0.0
                    desc = "; ".join(current_descriptions[:3]) if current_descriptions else ""

                    segments.append(VideoSegment(
                        video_path=video_path,
                        start_time=current_start,
                        end_time=current_end + self._frame_interval,
                        confidence=avg_conf,
                        description=desc or f"第一人称视角 [{current_start:.1f}s-{current_end:.1f}s]",
                    ))

                    current_start = None
                    current_end = None

        # 处理最后一个片段
        if current_start is not None:
            avg_conf = np.mean(current_confidences) if current_confidences else 0.0
            desc = "; ".join(current_descriptions[:3]) if current_descriptions else ""
            segments.append(VideoSegment(
                video_path=video_path,
                start_time=current_start,
                end_time=current_end + self._frame_interval,
                confidence=avg_conf,
                description=desc or f"第一人称视角 [{current_start:.1f}s-{current_end:.1f}s]",
            ))

        return segments

    def _filter_segments(self, segments: list[VideoSegment]) -> list[VideoSegment]:
        """过滤片段：时长控制在 9-60 秒"""
        filtered = []

        for seg in segments:
            duration = seg.end_time - seg.start_time

            # 时长过短 → 尝试合并到下一段（如果有）
            # 时长过长 → 拆分成多段
            if duration < self.MIN_SEGMENT_DURATION:
                # 太短的片段暂不保留（可调整策略）
                # 这里保留以增加候选多样性
                filtered.append(seg)
            elif duration > self.MAX_SEGMENT_DURATION:
                # 拆分成多个合理时长片段
                sub_segments = self._split_long_segment(seg)
                filtered.extend(sub_segments)
            else:
                filtered.append(seg)

        return filtered

    def _split_long_segment(self, seg: VideoSegment) -> list[VideoSegment]:
        """将过长片段拆分"""
        duration = seg.end_time - seg.start_time
        num_splits = int(np.ceil(duration / self.MAX_SEGMENT_DURATION))

        sub_segs = []
        sub_duration = duration / num_splits

        for i in range(num_splits):
            sub_start = seg.start_time + i * sub_duration
            sub_end = sub_start + sub_duration

            sub_segs.append(VideoSegment(
                video_path=seg.video_path,
                start_time=sub_start,
                end_time=sub_end,
                confidence=seg.confidence,
                description=f"{seg.description} (片段{i+1}/{num_splits})",
            ))

        return sub_segs


__all__ = [
    "FirstPersonExtractor",
    "VideoSegment",
    "VisionModel",
    "MockVisionModel",
]