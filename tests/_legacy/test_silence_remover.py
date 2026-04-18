#!/usr/bin/env python3
"""Test Silence Remover"""

import pytest
from dataclasses import asdict

from app.services.video_tools.silence_remover import (
    SilenceSegment,
    RemovalResult,
    SilenceRemover,
)


class TestSilenceSegment:
    """Test silence segment"""

    def test_creation(self):
        """Test creation"""
        segment = SilenceSegment(
            start_time=5.0,
            end_time=8.0,
            duration=3.0,
            confidence=0.95,
        )
        
        assert segment.start_time == 5.0
        assert segment.end_time == 8.0
        assert segment.duration == 3.0
        assert segment.confidence == 0.95

    def test_to_dict(self):
        """Test to dict"""
        segment = SilenceSegment(
            start_time=5.0,
            end_time=8.0,
            duration=3.0,
            confidence=0.95,
        )
        
        d = asdict(segment)
        
        assert d["start_time"] == 5.0
        assert d["end_time"] == 8.0
        assert d["duration"] == 3.0
        assert d["confidence"] == 0.95


class TestRemovalResult:
    """Test removal result"""

    def test_creation(self):
        """Test creation"""
        segments = [
            SilenceSegment(5.0, 8.0, 3.0, 0.95),
        ]
        
        result = RemovalResult(
            original_duration=120.0,
            new_duration=100.0,
            removed_segments=segments,
            keep_segments=[(0.0, 5.0), (8.0, 120.0)],
            compression_ratio=0.83,
        )
        
        assert result.original_duration == 120.0
        assert result.new_duration == 100.0
        assert len(result.removed_segments) == 1
        assert result.compression_ratio == 0.83


class TestSilenceRemover:
    """Test silence remover"""

    def test_init(self):
        """Test initialization"""
        remover = SilenceRemover()
        
        assert remover.silence_threshold_db == -40.0
        assert remover.min_silence_duration == 0.5

    def test_init_custom(self):
        """Test custom initialization"""
        remover = SilenceRemover(
            silence_threshold_db=-50.0,
            min_silence_duration=1.0,
        )
        
        assert remover.silence_threshold_db == -50.0
        assert remover.min_silence_duration == 1.0
