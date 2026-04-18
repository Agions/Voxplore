#!/usr/bin/env python3
"""测试第一人称独白制作器"""

import pytest
from dataclasses import asdict

from app.services.video.monologue_maker import (
    MonologueStyle,
    EmotionType,
    MonologueSegment,
    MonologueProject,
    MonologueMaker,
)


class TestMonologueStyle:
    """测试独白风格枚举"""

    def test_all_styles(self):
        """测试所有独白风格"""
        styles = [
            MonologueStyle.MELANCHOLIC,
            MonologueStyle.INSPIRATIONAL,
            MonologueStyle.ROMANTIC,
            MonologueStyle.MYSTERIOUS,
            MonologueStyle.NOSTALGIC,
            MonologueStyle.PHILOSOPHICAL,
            MonologueStyle.HEALING,
        ]
        
        assert len(styles) == 7
        assert MonologueStyle.MELANCHOLIC.value == "melancholic"


class TestEmotionType:
    """测试情感类型枚举"""

    def test_all_types(self):
        """测试所有情感类型"""
        types = [
            EmotionType.NEUTRAL,
            EmotionType.SAD,
            EmotionType.HAPPY,
        ]
        
        assert len(types) == 3
        assert EmotionType.NEUTRAL.value == "neutral"


class TestMonologueSegment:
    """测试独白片段"""

    def test_creation(self):
        """测试创建"""
        segment = MonologueSegment(
            script="内心独白...",
            video_start=5.0,
            video_end=10.0,
            emotion=EmotionType.SAD,
        )

        assert segment.script == "内心独白..."
        assert segment.video_start == 5.0
        assert segment.video_end == 10.0
        assert segment.emotion == EmotionType.SAD


class TestMonologueProject:
    """测试独白项目"""

    def test_creation(self):
        """测试创建"""
        project = MonologueProject(
            name="测试独白",
            source_video="/test/video.mp4",
            context="测试背景",
            emotion="惆怅",
        )
        
        assert project.name == "测试独白"
        assert project.context == "测试背景"


class TestMonologueMaker:
    """测试独白制作器"""

    def test_init(self):
        """测试初始化"""
        maker = MonologueMaker()
        
        assert maker.scene_analyzer is not None

    def test_init_custom_style(self):
        """测试自定义语音提供者（需要 API Key，跳过）"""
        pytest.skip("MonologueMaker.__init__ 需要 TTS API Key，需 mock")
