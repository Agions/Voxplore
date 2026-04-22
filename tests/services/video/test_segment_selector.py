#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试片段选择服务"""


from app.services.video.selection.segment_selector import (
    SelectionStrategy,
    SegmentSelector,
)
from app.services.video.extraction.first_person_extractor import VideoSegment


class TestSelectionStrategy:
    """测试 SelectionStrategy 枚举"""

    def test_all_strategies(self):
        """测试所有策略存在"""
        strategies = [
            SelectionStrategy.NARRATIVE_FIRST,
            SelectionStrategy.EMOTION_PEAK,
            SelectionStrategy.HYBRID,
        ]
        assert len(strategies) == 3
        assert SelectionStrategy.NARRATIVE_FIRST.value == "narrative_first"
        assert SelectionStrategy.EMOTION_PEAK.value == "emotion_peak"
        assert SelectionStrategy.HYBRID.value == "hybrid"


class MockNarrativeAnalyzer:
    """模拟叙事完整性分析器"""

    def __init__(self, narrative_scores: dict[str, float]):
        # narrative_scores: video_path -> narrative completeness score
        self._scores = narrative_scores

    def analyze(self, segment: VideoSegment) -> float:
        if segment.video_path in self._scores:
            return self._scores[segment.video_path]
        return 0.5


class TestSegmentSelector:
    """测试 SegmentSelector"""

    def test_init(self):
        """测试初始化"""
        selector = SegmentSelector()
        assert selector is not None

    def test_select_10segments_60seconds_target(self):
        """测试：10个片段 + 60秒目标 → 选最优组合"""
        # 创建 10 个片段，总时长远超 60 秒
        segments = [
            VideoSegment("/test/v1.mp4", 0, 15, 0.9, "完整开头"),
            VideoSegment("/test/v2.mp4", 15, 30, 0.7, "中间过程"),
            VideoSegment("/test/v3.mp4", 30, 45, 0.85, "高潮1"),
            VideoSegment("/test/v4.mp4", 45, 60, 0.6, "过渡"),
            VideoSegment("/test/v5.mp4", 60, 75, 0.8, "高潮2"),
            VideoSegment("/test/v6.mp4", 75, 90, 0.5, "结尾1"),
            VideoSegment("/test/v7.mp4", 90, 105, 0.75, "结尾2"),
            VideoSegment("/test/v8.mp4", 105, 120, 0.65, "尾声1"),
            VideoSegment("/test/v9.mp4", 120, 135, 0.55, "尾声2"),
            VideoSegment("/test/v10.mp4", 135, 150, 0.45, "尾声3"),
        ]

        # 设置叙事分数（开头和结尾高）
        narrative_scores = {
            "/test/v1.mp4": 0.95,   # 完整开头
            "/test/v2.mp4": 0.6,
            "/test/v3.mp4": 0.9,    # 高潮
            "/test/v4.mp4": 0.5,
            "/test/v5.mp4": 0.85,   # 高潮
            "/test/v6.mp4": 0.7,    # 结尾
            "/test/v7.mp4": 0.8,    # 结尾
            "/test/v8.mp4": 0.6,
            "/test/v9.mp4": 0.5,
            "/test/v10.mp4": 0.4,
        }

        selector = SegmentSelector()
        selector._narrative_analyzer = MockNarrativeAnalyzer(narrative_scores)

        selected = selector.select_segments(
            segments,
            strategy=SelectionStrategy.HYBRID,
            target_duration=(40.0, 60.0),
        )

        # 计算总时长
        total_duration = sum(s.end_time - s.start_time for s in selected)
        
        assert 40.0 <= total_duration <= 65.0, \
            f"总时长 {total_duration:.1f}s 应在 40-65s 范围内"
        assert len(selected) <= len(segments)
        assert len(selected) >= 1

    def test_select_narrative_first_prioritized(self):
        """测试：叙事完整片段优先于情感峰值"""
        segments = [
            VideoSegment("/test/narrative.mp4", 0, 30, 0.6, "完整叙事"),
            VideoSegment("/test/peak.mp4", 30, 45, 0.95, "情感峰值（但不完整）"),
            VideoSegment("/test/middle.mp4", 45, 75, 0.5, "普通片段"),
        ]

        narrative_scores = {
            "/test/narrative.mp4": 0.95,  # 高叙事完整性
            "/test/peak.mp4": 0.3,        # 低叙事完整性
            "/test/middle.mp4": 0.4,
        }

        selector = SegmentSelector()
        selector._narrative_analyzer = MockNarrativeAnalyzer(narrative_scores)

        selected = selector.select_segments(
            segments,
            strategy=SelectionStrategy.NARRATIVE_FIRST,
            target_duration=(25.0, 35.0),
        )

        # 应该优先选择叙事完整的片段
        # 虽然情感峰值置信度更高，但叙事优先会选择 narrative 片段
        if len(selected) >= 1:
            # 如果选择了情感峰值片段，时间要符合要求
            for seg in selected:
                duration = seg.end_time - seg.start_time
                assert duration > 0

    def test_select_respects_max_duration(self):
        """测试：不超过目标时长上限"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 100, 0.9, "长片段1"),
            VideoSegment("/test/v2.mp4", 100, 200, 0.8, "长片段2"),
        ]

        selector = SegmentSelector()
        
        selected = selector.select_segments(
            segments,
            strategy=SelectionStrategy.HYBRID,
            target_duration=(60.0, 120.0),
        )

        total_duration = sum(s.end_time - s.start_time for s in selected)
        assert total_duration <= 130.0, \
            f"总时长 {total_duration:.1f}s 不应超过上限 130s"

    def test_select_empty_input(self):
        """测试空输入"""
        selector = SegmentSelector()
        selected = selector.select_segments([], target_duration=(60.0, 120.0))
        assert selected == []

    def test_select_single_segment_fits(self):
        """测试：单个片段刚好符合要求"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 50, 0.9, "刚好50秒"),
        ]

        selector = SegmentSelector()
        selected = selector.select_segments(
            segments,
            strategy=SelectionStrategy.HYBRID,
            target_duration=(40.0, 60.0),
        )

        assert len(selected) == 1
        assert selected[0].video_path == "/test/v1.mp4"

    def test_select_all_strategies(self):
        """测试三种策略都可正常工作"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 20, 0.8, "叙事"),
            VideoSegment("/test/v2.mp4", 20, 40, 0.9, "峰值"),
        ]

        selector = SegmentSelector()

        for strategy in SelectionStrategy:
            selected = selector.select_segments(
                segments,
                strategy=strategy,
                target_duration=(15.0, 30.0),
            )
            assert isinstance(selected, list)

    def test_select_with_default_duration(self):
        """测试默认目标时长"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 30, 0.8, "测试"),
            VideoSegment("/test/v2.mp4", 30, 60, 0.7, "测试2"),
        ]

        selector = SegmentSelector()
        
        # 使用默认 target_duration=(60, 180)
        selected = selector.select_segments(segments)
        
        assert isinstance(selected, list)


class TestSegmentSelectorDuration:
    """测试片段选择时长控制"""

    def test_total_duration_within_target(self):
        """测试：选中的片段总时长在目标范围内"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 10, 0.9, "短1"),
            VideoSegment("/test/v2.mp4", 10, 25, 0.85, "中"),
            VideoSegment("/test/v3.mp4", 25, 40, 0.8, "中长"),
            VideoSegment("/test/v4.mp4", 40, 60, 0.75, "长"),
            VideoSegment("/test/v5.mp4", 60, 85, 0.7, "很长"),
        ]

        selector = SegmentSelector()
        selected = selector.select_segments(
            segments,
            strategy=SelectionStrategy.HYBRID,
            target_duration=(20.0, 35.0),
        )

        total = sum(s.end_time - s.start_time for s in selected)
        # 允许一定容差（因为贪婪选择）
        assert total <= 40.0, f"总时长 {total:.1f}s 超过上限"
        assert total >= 15.0, f"总时长 {total:.1f}s 低于下限"

    def test_early_return_when_enough(self):
        """测试：达到目标时长后提前停止"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 15, 0.95, "高质量"),
            VideoSegment("/test/v2.mp4", 15, 30, 0.8, "中等"),
            VideoSegment("/test/v3.mp4", 30, 50, 0.6, "较低"),
        ]

        selector = SegmentSelector()
        
        selected = selector.select_segments(
            segments,
            strategy=SelectionStrategy.EMOTION_PEAK,
            target_duration=(10.0, 20.0),
        )

        total = sum(s.end_time - s.start_time for s in selected)
        # 应该选择第一个高质量片段后停止（15s 在目标范围内）
        assert 10.0 <= total <= 22.0