#!/usr/bin/env python3
"""
SegmentSelector - 片段选择服务

功能：
叙事完整性优先 + 情感峰值驱动：
1. 优先选有头有尾的完整片段
2. 情感峰值片段加权
3. 总时长在 target_duration 范围内
4. 返回最优片段组合
"""

from enum import Enum
from typing import Protocol, runtime_checkable

from scenefab.services.video.extraction.first_person import VideoSegment


class SelectionStrategy(Enum):
    """选择策略枚举"""

    NARRATIVE_FIRST = "narrative_first"  # 叙事完整性优先
    EMOTION_PEAK = "emotion_peak"  # 情感峰值优先
    HYBRID = "hybrid"  # 混合策略


@runtime_checkable
class NarrativeAnalyzer(Protocol):
    """叙事完整性分析器协议

    实现此协议以接入真实叙事分析模型
    """

    def analyze(self, segment: VideoSegment) -> float:
        """分析片段的叙事完整性

        Args:
            segment: 视频片段

        Returns:
            叙事完整性评分（0.0 ~ 1.0）
        """
        ...


class MockNarrativeAnalyzer:
    """模拟叙事完整性分析器（用于测试和开发）"""

    def analyze(self, segment: VideoSegment) -> float:
        # 模拟：基于时长和描述判断叙事完整性
        duration = segment.end_time - segment.start_time

        # 中等时长（15-45秒）通常叙事更完整
        if 15.0 <= duration <= 45.0:
            base_score = 0.7
        elif duration < 15.0:
            base_score = 0.4  # 太短可能不完整
        else:
            base_score = 0.6  # 较长可能拖沓

        # 描述中包含"完整"等词加分
        if "完整" in segment.description:
            base_score += 0.2

        return min(1.0, max(0.0, base_score))


class SegmentSelector:
    """片段选择器"""

    def __init__(
        self,
        narrative_analyzer: NarrativeAnalyzer | None = None,
    ):
        """初始化选择器

        Args:
            narrative_analyzer: 叙事完整性分析器（默认使用 Mock）
        """
        self._narrative_analyzer = narrative_analyzer or MockNarrativeAnalyzer()

    def select_segments(
        self,
        segments: list[VideoSegment],
        strategy: SelectionStrategy = SelectionStrategy.HYBRID,
        target_duration: tuple[float, float] = (60.0, 180.0),
    ) -> list[VideoSegment]:
        """选择最优片段组合

        Args:
            segments: 候选片段列表
            strategy: 选择策略
            target_duration: 目标时长范围 (min, max)，秒

        Returns:
            选中的片段列表
        """
        if not segments:
            return []

        min_duration, max_duration = target_duration

        selector_map = {
            SelectionStrategy.NARRATIVE_FIRST: self._select_narrative_first,
            SelectionStrategy.EMOTION_PEAK: self._select_emotion_peak,
            SelectionStrategy.HYBRID: self._select_hybrid,
        }
        selector = selector_map.get(strategy, self._select_hybrid)
        return selector(segments, min_duration, max_duration)

    def _select_narrative_first(
        self,
        segments: list[VideoSegment],
        min_duration: float,
        max_duration: float,
    ) -> list[VideoSegment]:
        """叙事完整性优先策略"""
        scored = []
        for segment in segments:
            narrative_score = self._narrative_analyzer.analyze(segment)
            combined = 0.7 * narrative_score + 0.3 * segment.confidence
            scored.append((combined, segment))

        scored.sort(key=lambda item: item[0], reverse=True)
        return self._greedy_select(scored, min_duration, max_duration)

    def _select_emotion_peak(
        self,
        segments: list[VideoSegment],
        min_duration: float,
        max_duration: float,
    ) -> list[VideoSegment]:
        """情感峰值优先策略"""
        scored = [(segment.confidence, segment) for segment in segments]
        scored.sort(key=lambda item: item[0], reverse=True)

        return self._greedy_select(scored, min_duration, max_duration)

    def _select_hybrid(
        self,
        segments: list[VideoSegment],
        min_duration: float,
        max_duration: float,
    ) -> list[VideoSegment]:
        """混合策略：叙事 + 情感峰值平衡"""
        scored = []
        for segment in segments:
            narrative_score = self._narrative_analyzer.analyze(segment)
            combined = 0.5 * narrative_score + 0.5 * segment.confidence
            scored.append((combined, segment))

        scored.sort(key=lambda item: item[0], reverse=True)
        return self._greedy_select(scored, min_duration, max_duration)

    def _greedy_select(
        self,
        scored: list[tuple[float, VideoSegment]],
        min_duration: float,
        max_duration: float,
    ) -> list[VideoSegment]:
        """贪婪选择片段直到达到目标时长"""
        selected = []
        total_duration = 0.0

        for _, segment in scored:
            segment_duration = segment.end_time - segment.start_time

            if total_duration + segment_duration > max_duration * 1.05:
                continue

            selected.append(segment)
            total_duration += segment_duration

            if total_duration >= min_duration:
                break

        return selected


__all__ = [
    "SegmentSelector",
    "SelectionStrategy",
    "NarrativeAnalyzer",
    "MockNarrativeAnalyzer",
]
