#!/usr/bin/env python3
"""Test Scene Analyzer"""

from dataclasses import asdict

from app.services.ai.scene_analyzer import (
    SceneType,
    SceneInfo,
    AnalysisConfig,
    SceneAnalyzer,
)


class TestSceneType:
    """Test scene type enum"""

    def test_all_types(self):
        """Test all scene types"""
        types = [
            SceneType.TALKING_HEAD,
            SceneType.B_ROLL,
            SceneType.TITLE,
            SceneType.TRANSITION,
            SceneType.ACTION,
            SceneType.LANDSCAPE,
            SceneType.PRODUCT,
            SceneType.UNKNOWN,
        ]
        
        assert len(types) == 8
        assert SceneType.LANDSCAPE.value == "landscape"


class TestSceneInfo:
    """Test scene info"""

    def test_creation(self):
        """Test creation"""
        scene = SceneInfo(
            index=0,
            start=0.0,
            end=5.0,
            duration=5.0,
            type=SceneType.LANDSCAPE,
        )
        
        assert scene.index == 0
        assert scene.start == 0.0
        assert scene.end == 5.0
        assert scene.type == SceneType.LANDSCAPE

    def test_to_dict(self):
        """Test to dict"""
        scene = SceneInfo(
            index=0,
            start=0.0,
            end=5.0,
            duration=5.0,
            type=SceneType.LANDSCAPE,
        )
        
        d = asdict(scene)
        
        assert d["index"] == 0
        assert d["start"] == 0.0
        assert d["end"] == 5.0
        assert d["type"] == SceneType.LANDSCAPE


class TestAnalysisConfig:
    """Test analysis config"""

    def test_default_config(self):
        """Test default config"""
        config = AnalysisConfig()
        
        assert config.scene_threshold == 0.3
        assert config.min_scene_duration == 0.5

    def test_custom_config(self):
        """Test custom config"""
        config = AnalysisConfig(
            min_scene_duration=1.0,
            scene_threshold=0.5,
        )
        
        assert config.min_scene_duration == 1.0
        assert config.scene_threshold == 0.5


class TestSceneAnalyzer:
    """Test scene analyzer"""

    def test_init(self):
        """Test initialization"""
        analyzer = SceneAnalyzer()
        
        assert analyzer.config is not None
        assert isinstance(analyzer.config, AnalysisConfig)

    def test_init_custom_config(self):
        """Test custom config initialization"""
        config = AnalysisConfig(min_scene_duration=2.0)
        analyzer = SceneAnalyzer(config)
        
        assert analyzer.config.min_scene_duration == 2.0
