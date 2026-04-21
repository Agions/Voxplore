#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

from app.services.video.extraction.first_person_extractor import VideoSegment


class SelectionStrategy(Enum):
    """选择策略枚举"""
    NARRATIVE_FIRST = "narrative_first"  # 叙事完整性优先
    EMOTION_PEAK = "emotion_peak"       # 情感峰值优先
    HYBRID = "hybrid"                   # 混合策略


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
        
        if strategy == SelectionStrategy.NARRATIVE_FIRST:
            return self._select_narrative_first(segments, min_duration, max_duration)
        elif strategy == SelectionStrategy.EMOTION_PEAK:
            return self._select_emotion_peak(segments, min_duration, max_duration)
        else:  # HYBRID
            return self._select_hybrid(segments, min_duration, max_duration)
    
    def _select_narrative_first(
        self,
        segments: list[VideoSegment],
        min_duration: float,
        max_duration: float,
    ) -> list[VideoSegment]:
        """叙事完整性优先策略"""
        # 计算每个片段的综合分数（叙事为主，置信度辅助）
        scored = []
        for seg in segments:
            narrative_score = self._narrative_analyzer.analyze(seg)
            combined = 0.7 * narrative_score + 0.3 * seg.confidence
            scored.append((combined, seg))
        
        # 按综合分数降序排列
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # 贪婪选择
        return self._greedy_select(scored, min_duration, max_duration)
    
    def _select_emotion_peak(
        self,
        segments: list[VideoSegment],
        min_duration: float,
        max_duration: float,
    ) -> list[VideoSegment]:
        """情感峰值优先策略"""
        # 按置信度降序排列（情感峰值用 confidence 表示）
        scored = [(seg.confidence, seg) for seg in segments]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return self._greedy_select(scored, min_duration, max_duration)
    
    def _select_hybrid(
        self,
        segments: list[VideoSegment],
        min_duration: float,
        max_duration: float,
    ) -> list[VideoSegment]:
        """混合策略：叙事 + 情感峰值平衡"""
        scored = []
        for seg in segments:
            narrative_score = self._narrative_analyzer.analyze(seg)
            # 混合评分：叙事 0.5 + 情感 0.5
            combined = 0.5 * narrative_score + 0.5 * seg.confidence
            scored.append((combined, seg))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
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
        
        for _, seg in scored:
            seg_duration = seg.end_time - seg.start_time
            
            # 检查加入后是否超过上限
            if total_duration + seg_duration > max_duration * 1.05:  # 5% 容差
                continue
            
            selected.append(seg)
            total_duration += seg_duration
            
            # 达到目标下限后停止
            if total_duration >= min_duration:
                break
        
        return selected


__all__ = [
    "SegmentSelector",
    "SelectionStrategy",
    "NarrativeAnalyzer",
    "MockNarrativeAnalyzer",
]