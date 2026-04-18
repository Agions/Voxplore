#!/usr/bin/env python3
"""Test Pace Analyzer"""

import pytest
from dataclasses import asdict

from app.services.video_tools.pace_analyzer import (
    PaceLevel,
    PaceMetrics,
    SceneChange,
    PaceAnalysisResult,
    PaceAnalyzer,
)


class TestPaceLevel:
    """Test pace level enum"""

    def test_all_levels(self):
        """Test all pace levels"""
        levels = [
            PaceLevel.SLOW,
            PaceLevel.MODERATE,
            PaceLevel.FAST,
            PaceLevel.VIRAL,
        ]
        
        assert len(levels) == 4


class TestPaceMetrics:
    """Test pace metrics"""

    def test_creation(self):
        """Test creation"""
        metrics = PaceMetrics(
            cuts_per_minute=20.0,
            avg_shot_duration=2.0,
            visual_change_rate=0.8,
            audio_energy_variance=0.5,
            pace_level=PaceLevel.FAST,
            viral_score=75.0,
        )
        
        assert metrics.cuts_per_minute == 20.0
        assert metrics.avg_shot_duration == 2.0
        assert metrics.pace_level == PaceLevel.FAST


class TestSceneChange:
    """Test scene change"""

    def test_creation(self):
        """Test creation"""
        change = SceneChange(
            timestamp=5.0,
            score=0.8,
            type="cut",
        )
        
        assert change.timestamp == 5.0
        assert change.score == 0.8
        assert change.type == "cut"


class TestPaceAnalysisResult:
    """Test pace analysis result"""

    def test_creation(self):
        """Test creation"""
        metrics = PaceMetrics(
            cuts_per_minute=20.0,
            avg_shot_duration=2.0,
            visual_change_rate=0.8,
            audio_energy_variance=0.5,
            pace_level=PaceLevel.FAST,
            viral_score=75.0,
        )
        
        result = PaceAnalysisResult(
            video_duration=60.0,
            metrics=metrics,
            scene_changes=[],
            energy_curve=[],
            recommendations=[],
            hook_quality=85.0,
        )
        
        assert result.video_duration == 60.0
        assert result.metrics.cuts_per_minute == 20.0
        assert result.hook_quality == 85.0


class TestPaceAnalyzer:
    """Test pace analyzer"""

    def test_init(self):
        """Test initialization"""
        analyzer = PaceAnalyzer()
        
        assert analyzer is not None
        assert hasattr(analyzer, 'VIRAL_THRESHOLDS')

    def test_viral_thresholds(self):
        """Test viral thresholds constant"""
        thresholds = PaceAnalyzer.VIRAL_THRESHOLDS
        
        assert thresholds['min_cpm'] == 15.0
        assert thresholds['min_hook_duration'] == 3.0
