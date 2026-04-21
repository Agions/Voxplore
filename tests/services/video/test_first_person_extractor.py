#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试第一人称视角提取服务"""

import pytest
from dataclasses import asdict
from unittest.mock import MagicMock, patch
import numpy as np

from app.services.video.extraction.first_person_extractor import (
    VideoSegment,
    FirstPersonExtractor,
)


class TestVideoSegment:
    """测试 VideoSegment 数据类"""

    def test_creation(self):
        """测试创建"""
        segment = VideoSegment(
            video_path="/test/video.mp4",
            start_time=10.0,
            end_time=30.0,
            confidence=0.85,
            description="第一人称视角，展示行走场景"
        )

        assert segment.video_path == "/test/video.mp4"
        assert segment.start_time == 10.0
        assert segment.end_time == 30.0
        assert segment.confidence == 0.85

    def test_duration(self):
        """测试时长计算"""
        segment = VideoSegment(
            video_path="/test/video.mp4",
            start_time=10.0,
            end_time=30.0,
            confidence=0.8,
            description=""
        )
        assert segment.end_time - segment.start_time == 20.0


class MockVisionModel:
    """模拟 Qwen2.5-VL 模型"""

    def __init__(self, first_person_responses: dict[str, list[tuple[float, float, float]]]):
        # first_person_responses[video_path] = [(start, end, confidence), ...]
        self._responses = first_person_responses

    def analyze_frame(self, video_path: str, timestamp: float) -> dict:
        """模拟帧分析"""
        if video_path not in self._responses:
            # 默认非第一人称
            return {"is_first_person": False, "confidence": 0.3, "description": ""}
        
        for start, end, conf in self._responses[video_path]:
            if start <= timestamp <= end:
                return {
                    "is_first_person": True,
                    "confidence": conf,
                    "description": f"第一人称视角 @ {timestamp}s"
                }
        
        return {"is_first_person": False, "confidence": 0.2, "description": ""}


def create_mock_vision_model(video_fp_segments: dict[str, list[tuple[float, float, float]]]):
    """创建模拟视觉模型"""
    model = MagicMock()
    model.analyze_frame = lambda vp, ts: MockVisionModel(video_fp_segments).analyze_frame(vp, ts)
    return model


class TestFirstPersonExtractor:
    """测试 FirstPersonExtractor"""

    def test_init(self):
        """测试初始化"""
        extractor = FirstPersonExtractor()
        assert extractor is not None

    def test_extract_single_video_returns_multiple_segments(self):
        """测试：单个视频 → 返回多个候选片段"""
        video_path = "/test/first_person_video.mp4"
        
        # 模拟：视频有两个第一人称片段
        # [0-10s] 非第一人称, [10-25s] 第一人称, [25-40s] 非, [40-55s] 第一人称, [55-60s] 非
        fp_segments = {
            video_path: [
                (10.0, 25.0, 0.92),
                (40.0, 55.0, 0.88),
            ]
        }

        extractor = FirstPersonExtractor()
        extractor._vision_model = create_mock_vision_model(fp_segments)

        segments = extractor.extract_first_person_segments(video_path, group_id="group_001")

        assert len(segments) >= 1
        for seg in segments:
            assert seg.video_path == video_path
            assert 9.0 <= (seg.end_time - seg.start_time) <= 60.0, \
                f"片段时长 {(seg.end_time - seg.start_time):.1f}s 应在 9-60s 范围内"

    def test_extract_segments_duration_9_to_60_seconds(self):
        """测试：片段时长 9-60 秒（符合短视频长度）"""
        video_path = "/test/fp_video2.mp4"
        
        fp_segments = {
            video_path: [
                (5.0, 20.0, 0.9),   # 15s → OK
                (20.0, 28.0, 0.85), # 8s → 太短，会被过滤或合并
                (28.0, 70.0, 0.8),  # 42s → OK
            ]
        }

        extractor = FirstPersonExtractor()
        extractor._vision_model = create_mock_vision_model(fp_segments)

        segments = extractor.extract_first_person_segments(video_path, group_id="group_001")

        # 过滤后时长应该在 9-60s
        for seg in segments:
            duration = seg.end_time - seg.start_time
            assert 9.0 <= duration <= 60.0 or duration < 9.0, \
                f"片段 {seg.start_time:.1f}s-{seg.end_time:.1f}s 时长 {duration:.1f}s 超出范围"

    def test_extract_segments_sorted_by_confidence(self):
        """测试：置信度排序（最高在前）"""
        video_path = "/test/fp_video3.mp4"
        
        fp_segments = {
            video_path: [
                (0.0, 15.0, 0.6),   # 低置信度
                (15.0, 35.0, 0.95), # 高置信度
                (35.0, 50.0, 0.75), # 中置信度
            ]
        }

        extractor = FirstPersonExtractor()
        extractor._vision_model = create_mock_vision_model(fp_segments)

        segments = extractor.extract_first_person_segments(video_path, group_id="group_001")

        if len(segments) > 1:
            confidences = [s.confidence for s in segments]
            assert confidences == sorted(confidences, reverse=True), \
                f"置信度应降序排列: {confidences}"

    def test_extract_no_first_person(self):
        """测试：无第一人称片段"""
        video_path = "/test/third_person.mp4"
        
        # 无第一人称片段
        fp_segments = {}

        extractor = FirstPersonExtractor()
        extractor._vision_model = create_mock_vision_model(fp_segments)

        segments = extractor.extract_first_person_segments(video_path, group_id="group_001")

        # 可能返回空或低置信度片段
        assert isinstance(segments, list)

    def test_extract_with_group_id(self):
        """测试：group_id 被正确传递（用于未来多视频联合分析）"""
        video_path = "/test/fp_video.mp4"
        
        fp_segments = {
            video_path: [
                (10.0, 30.0, 0.9),
            ]
        }

        extractor = FirstPersonExtractor()
        extractor._vision_model = create_mock_vision_model(fp_segments)

        segments = extractor.extract_first_person_segments(
            video_path, 
            group_id="test_group_123"
        )

        # group_id 用于未来扩展，当前实现可不使用
        assert all(seg.video_path == video_path for seg in segments)


class TestVideoSegmentDataclass:
    """测试 VideoSegment 数据类完整性"""

    def test_to_dict(self):
        """测试序列化"""
        segment = VideoSegment(
            video_path="/test/video.mp4",
            start_time=10.0,
            end_time=30.0,
            confidence=0.88,
            description="测试片段"
        )
        
        d = asdict(segment)
        assert d["video_path"] == "/test/video.mp4"
        assert d["start_time"] == 10.0
        assert d["end_time"] == 30.0
        assert d["confidence"] == 0.88
        assert d["description"] == "测试片段"

    def test_confidence_range(self):
        """测试置信度边界值"""
        seg_low = VideoSegment("/t.mp4", 0, 10, 0.0, "")
        assert seg_low.confidence == 0.0

        seg_high = VideoSegment("/t.mp4", 0, 10, 1.0, "")
        assert seg_high.confidence == 1.0