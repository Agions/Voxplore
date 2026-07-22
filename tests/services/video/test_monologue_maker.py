#!/usr/bin/env python3
"""测试第一人称独白制作器"""

import pytest

from scenefab.services.video import monologue_maker as maker_module
from scenefab.services.video.monologue_maker import (
    EmotionType,
    MonologueMaker,
    MonologueProject,
    MonologueSegment,
    MonologueStyle,
)


class DummyVoiceGenerator:
    """Offline voice generator for constructor tests."""

    def __init__(self, provider: str = "edge"):
        self.provider = provider


class DummyScriptGenerator:
    """Offline script generator for constructor tests."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class DummyCaptionGenerator:
    """Offline caption generator for constructor tests."""

    pass


@pytest.fixture
def offline_dependencies(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(maker_module, "VoiceGenerator", DummyVoiceGenerator)
    monkeypatch.setattr(maker_module, "ScriptGenerator", DummyScriptGenerator)
    monkeypatch.setattr(maker_module, "CaptionGenerator", DummyCaptionGenerator)


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

    def test_init(self, offline_dependencies):
        """测试初始化"""
        maker = MonologueMaker()

        assert maker.scene_analyzer is not None
        assert isinstance(maker.voice_generator, DummyVoiceGenerator)
        assert isinstance(maker.script_generator, DummyScriptGenerator)
        assert isinstance(maker.caption_generator, DummyCaptionGenerator)

    def test_init_custom_voice_provider(self, offline_dependencies):
        """测试自定义语音提供者"""
        maker = MonologueMaker(voice_provider="openai")

        assert maker.voice_provider == "openai"
        assert maker.voice_generator.provider == "openai"
