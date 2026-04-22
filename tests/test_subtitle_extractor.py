#!/usr/bin/env python3
"""Test Subtitle Extractor"""

from dataclasses import asdict

from app.services.ai.subtitle_extractor import (
    SubtitleSegment,
    SubtitleExtractionResult,
)


class TestSubtitleSegment:
    """Test subtitle segment"""

    def test_creation(self):
        """Test creation"""
        segment = SubtitleSegment(
            start=0.0,
            end=3.5,
            text="第一句台词",
            confidence=0.95,
            source="speech",
        )
        
        assert segment.start == 0.0
        assert segment.end == 3.5
        assert segment.text == "第一句台词"
        assert segment.confidence == 0.95
        assert segment.source == "speech"

    def test_default_values(self):
        """Test default values"""
        segment = SubtitleSegment(
            start=0.0,
            end=1.0,
            text="测试",
        )
        
        assert segment.confidence == 1.0
        assert segment.source == ""

    def test_to_dict(self):
        """Test to dict"""
        segment = SubtitleSegment(
            start=0.0,
            end=1.0,
            text="测试",
        )
        
        d = asdict(segment)
        
        assert d["start"] == 0.0
        assert d["text"] == "测试"


class TestSubtitleExtractionResult:
    """Test subtitle extraction result"""

    def test_creation(self):
        """Test creation"""
        segments = [
            SubtitleSegment(0.0, 1.0, "第一句"),
            SubtitleSegment(1.0, 2.0, "第二句"),
        ]
        
        result = SubtitleExtractionResult(
            video_path="/test/video.mp4",
            duration=120.0,
            segments=segments,
            full_text="第一句 第二句",
            language="zh",
            method="speech",
        )
        
        assert result.video_path == "/test/video.mp4"
        assert result.duration == 120.0
        assert len(result.segments) == 2
        assert result.full_text == "第一句 第二句"

    def test_default_values(self):
        """Test default values"""
        result = SubtitleExtractionResult(
            video_path="/test.mp4",
            duration=60.0,
        )
        
        assert result.segments == []
        assert result.full_text == ""
        assert result.language == "zh"
        assert result.method == ""

    def test_full_text_from_segments(self):
        """Test full text from segments"""
        segments = [
            SubtitleSegment(0.0, 1.0, "你好"),
            SubtitleSegment(1.0, 2.0, "世界"),
        ]
        
        result = SubtitleExtractionResult(
            video_path="/test.mp4",
            duration=2.0,
            segments=segments,
        )
        
        # Should be able to combine text from segments
        full_text = " ".join(s.text for s in result.segments)
        assert "你好" in full_text
        assert "世界" in full_text
        assert result.method == ""
