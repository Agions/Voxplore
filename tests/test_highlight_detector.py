#!/usr/bin/env python3
"""测试高光检测器"""

import pytest
from voxplore.services.video import (
    HighlightDetector,
    HighlightSegment,
    HighlightReason,
    HighlightDetectorConfig,
)


class TestHighlightDetector:
    """测试高光检测器"""

    def test_creation(self):
        """测试创建"""
        detector = HighlightDetector()
        assert detector is not None
        assert detector.config is not None

    def test_creation_with_config(self):
        """测试使用自定义配置创建"""
        config = HighlightDetectorConfig(
            min_confidence=0.7,
            scene_change_weight=0.4,
            audio_peak_weight=0.3,
        )
        detector = HighlightDetector(config)
        assert detector.config.min_confidence == 0.7
        assert detector.config.scene_change_weight == 0.4

    def test_config_defaults(self):
        """测试默认配置"""
        config = HighlightDetectorConfig()
        assert config.min_duration == 1.0
        assert config.max_duration == 30.0
        assert config.min_gap == 0.5
        assert config.min_confidence == 0.5
        assert config.scene_change_weight == 0.3
        assert config.audio_peak_weight == 0.4
        assert config.motion_weight == 0.2
        assert config.color_weight == 0.1

    def test_detect_file_not_found(self):
        """测试文件不存在时抛出异常"""
        detector = HighlightDetector()
        with pytest.raises(FileNotFoundError):
            detector.detect("/nonexistent/video.mp4")

    def test_highlight_segment_properties(self):
        """测试高光片段属性"""
        segment = HighlightSegment(
            start=1.0,
            end=3.0,
            confidence=0.8,
            reason=HighlightReason.AUDIO_PEAK,
            peak_timestamp=2.0,
        )
        assert segment.duration == 2.0
        assert segment.start == 1.0
        assert segment.end == 3.0
        assert segment.confidence == 0.8
        assert segment.reason == HighlightReason.AUDIO_PEAK

    def test_highlight_segment_to_dict(self):
        """测试高光片段转换为字典"""
        segment = HighlightSegment(
            start=1.0,
            end=3.0,
            confidence=0.8,
            reason=HighlightReason.SCENE_CHANGE,
            peak_timestamp=2.0,
        )
        d = segment.to_dict()
        assert d["start"] == 1.0
        assert d["end"] == 3.0
        assert d["duration"] == 2.0
        assert d["confidence"] == 0.8
        assert d["reason"] == "scene_change"
        assert d["peak_timestamp"] == 2.0

    def test_highlight_reason_enum(self):
        """测试高光原因枚举"""
        assert HighlightReason.SCENE_CHANGE.value == "scene_change"
        assert HighlightReason.AUDIO_PEAK.value == "audio_peak"
        assert HighlightReason.MOTION_INTENSE.value == "motion_intense"
        assert HighlightReason.COLOR_VIBRANT.value == "color_vibrant"
        assert HighlightReason.COMBINED.value == "combined"
