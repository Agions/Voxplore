#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试 - 文案生成器
"""

import pytest
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ai.script_generator import (
    ScriptStyle,
    VoiceTone,
    ScriptConfig,
    GeneratedScript,
    ScriptSegment,
)


class TestScriptConfig:
    """测试文案配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = ScriptConfig()

        assert config.style == ScriptStyle.COMMENTARY
        assert config.tone == VoiceTone.NEUTRAL
        assert config.target_duration == 60.0
        assert config.words_per_second == 3.0
        assert config.target_words == 180

    def test_viral_style_config(self):
        """测试爆款风格配置"""
        config = ScriptConfig(
            style=ScriptStyle.VIRAL,
            target_duration=30.0,
        )

        assert config.style == ScriptStyle.VIRAL
        assert config.target_words == 90


class TestGeneratedScript:
    """测试生成的文案"""

    def test_create_script(self):
        """测试创建文案"""
        script = GeneratedScript(
            content="这是测试文案内容",
            style=ScriptStyle.COMMENTARY,
            word_count=8,
            estimated_duration=2.67,
        )

        assert script.content == "这是测试文案内容"
        assert script.style == ScriptStyle.COMMENTARY
        assert script.word_count == 8
        assert script.estimated_duration == 2.67

    def test_script_auto_word_count(self):
        """测试自动计算字数"""
        script = GeneratedScript(content="测试字数")
        assert script.word_count == 4


class TestScriptStyle:
    """测试文案风格枚举"""

    def test_style_values(self):
        """测试风格值"""
        assert ScriptStyle.COMMENTARY.value == "commentary"
        assert ScriptStyle.MONOLOGUE.value == "monologue"
        assert ScriptStyle.VIRAL.value == "viral"
        assert ScriptStyle.NARRATION.value == "narration"
        assert ScriptStyle.EDUCATIONAL.value == "educational"


class TestVoiceTone:
    """测试语气枚举"""

    def test_tone_values(self):
        """测试语气值"""
        assert VoiceTone.NEUTRAL.value == "neutral"
        assert VoiceTone.EXCITED.value == "excited"
        assert VoiceTone.EMOTIONAL.value == "emotional"
