#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EmotionPeakDetector - 情感峰值检测服务

功能：
1. 画面信息密度检测（复杂度/动作密度）
2. 情绪起伏检测（音频语调变化）
3. 综合评分排序
4. 返回峰值片段（降序排列）
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
import logging

logger = logging.getLogger(__name__)

from app.services.video.extraction.first_person_extractor import VideoSegment


@dataclass
class EmotionPeak:
    """情感峰值"""
    segment: VideoSegment
    peak_score: float  # 综合评分
    reason: str  # 峰值原因（高复杂度/强情绪/动作密度）


@runtime_checkable
class VisualComplexityAnalyzer(Protocol):
    """视觉复杂度分析器协议

    实现此协议以接入真实视觉分析模型
    """

    def analyze(self, video_path: str, start: float, end: float) -> float:
        """分析视觉复杂度

        Args:
            video_path: 视频路径
            start: 开始时间（秒）
            end: 结束时间（秒）

        Returns:
            复杂度评分（0.0 ~ 1.0）
        """
        ...


@runtime_checkable
class AudioEmotionAnalyzer(Protocol):
    """音频情绪分析器协议

    实现此协议以接入真实音频情绪识别模型
    """

    def analyze(self, video_path: str, start: float, end: float) -> float:
        """分析音频情绪强度

        Args:
            video_path: 视频路径
            start: 开始时间（秒）
            end: 结束时间（秒）

        Returns:
            情绪评分（0.0 ~ 1.0）
        """
        ...


class MockVisualComplexityAnalyzer:
    """模拟视觉复杂度分析器（用于测试和开发）"""

    def analyze(self, video_path: str, start: float, end: float) -> float:
        # 模拟：基于路径和时长生成伪随机复杂度
        hash_val = hash(video_path + f"{start:.1f}") % (2**20)
        base = (hash_val % 100) / 100.0
        return max(0.0, min(1.0, base))


class MockAudioEmotionAnalyzer:
    """模拟音频情绪分析器（用于测试和开发）"""

    def analyze(self, video_path: str, start: float, end: float) -> float:
        # 模拟：默认中等情绪
        hash_val = hash(video_path + f"{end:.1f}") % (2**20)
        base = (hash_val % 80) / 100.0
        return max(0.0, min(1.0, base))


class EmotionPeakDetector:
    """情感峰值检测器"""

    # 评分权重
    VISUAL_WEIGHT = 0.6
    AUDIO_WEIGHT = 0.4

    # 最低峰值阈值（低于此值不返回）
    MIN_PEAK_THRESHOLD = 0.4

    def __init__(
        self,
        visual_analyzer: VisualComplexityAnalyzer | None = None,
        audio_analyzer: AudioEmotionAnalyzer | None = None,
        visual_weight: float = VISUAL_WEIGHT,
        audio_weight: float = AUDIO_WEIGHT,
        min_peak_threshold: float = MIN_PEAK_THRESHOLD,
    ):
        """初始化检测器

        Args:
            visual_analyzer: 视觉复杂度分析器（默认使用 Mock）
            audio_analyzer: 音频情绪分析器（默认使用 Mock）
            visual_weight: 视觉权重
            audio_weight: 音频权重
            min_peak_threshold: 最低峰值阈值
        """
        self._visual_analyzer = visual_analyzer or MockVisualComplexityAnalyzer()
        self._audio_analyzer = audio_analyzer or MockAudioEmotionAnalyzer()
        self._visual_weight = visual_weight
        self._audio_weight = audio_weight
        self._min_peak_threshold = min_peak_threshold

    def detect_peaks(
        self,
        segments: list[VideoSegment],
    ) -> list[EmotionPeak]:
        """检测情感峰值

        Args:
            segments: 视频片段列表

        Returns:
            情感峰值列表（按峰值评分降序排列）
        """
        if not segments:
            return []

        peaks = []

        for seg in segments:
            # 计算视觉复杂度
            try:
                visual_score = self._visual_analyzer.analyze(
                    seg.video_path,
                    seg.start_time,
                    seg.end_time,
                )
            except Exception as e:
                logger.warning(f"Visual analysis failed for segment {seg.segment_id}: {e}")
                visual_score = 0.5

            # 计算音频情绪
            try:
                audio_score = self._audio_analyzer.analyze(
                    seg.video_path,
                    seg.start_time,
                    seg.end_time,
                )
            except Exception as e:
                logger.warning(f"Audio analysis failed for segment {seg.segment_id}: {e}")
                audio_score = 0.5

            # 综合评分
            peak_score = (
                self._visual_weight * visual_score +
                self._audio_weight * audio_score
            )

            # 低于阈值跳过
            if peak_score < self._min_peak_threshold:
                continue

            # 判断峰值原因
            reason = self._determine_reason(
                visual_score, audio_score, seg.description
            )

            peaks.append(EmotionPeak(
                segment=seg,
                peak_score=peak_score,
                reason=reason,
            ))

        # 按峰值评分降序排列
        peaks.sort(key=lambda p: p.peak_score, reverse=True)

        return peaks

    def _determine_reason(
        self,
        visual_score: float,
        audio_score: float,
        description: str,
    ) -> str:
        """判断峰值原因"""
        if visual_score > audio_score * 1.5:
            # 视觉主导
            if visual_score > 0.8:
                return "高复杂度场景，信息密度大"
            elif visual_score > 0.6:
                return "动作密度较高"
            else:
                return "画面信息丰富"
        elif audio_score > visual_score * 1.5:
            # 音频主导
            return "音频情绪强度高"
        else:
            # 综合
            if visual_score > 0.7 and audio_score > 0.7:
                return "视觉+音频双重高能"
            elif visual_score > 0.6:
                return "综合情感峰值"
            else:
                return "情感起伏明显"


__all__ = [
    "EmotionPeakDetector",
    "EmotionPeak",
    "VisualComplexityAnalyzer",
    "AudioEmotionAnalyzer",
    "MockVisualComplexityAnalyzer",
    "MockAudioEmotionAnalyzer",
]