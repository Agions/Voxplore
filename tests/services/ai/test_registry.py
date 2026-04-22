#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 AI Provider 注册表"""

import pytest
import tempfile
import os

from app.services.ai.registry import ProviderRegistry
from app.services.ai.interfaces import (
    VisionProvider,
    LLMProvider,
    TTSProvider,
    VideoAnalysis,
    ScriptResult,
    AudioData,
)


# =============================================================================
# Mock Providers
# =============================================================================

class MockVisionProvider(VisionProvider):
    """模拟视觉理解 Provider"""

    def analyze_video(self, video_path: str) -> VideoAnalysis:
        return VideoAnalysis(
            summary="测试摘要",
            tags=["test", "video"],
            scene_changes=[1.0, 2.5, 5.0],
        )

    def extract_keyframes(self, video_path: str, count: int) -> list[bytes]:
        return [b"fake_frame" for _ in range(count)]


class MockLLMProvider(LLMProvider):
    """模拟大语言 Model Provider"""

    def generate_script(self, prompt: str, style: str | None = None) -> ScriptResult:
        return ScriptResult(
            script=f"测试脚本: {prompt}",
            style=style or "default",
            character="旁白",
        )

    def generate_narration(self, context: str, character: str | None = None) -> str:
        return f"测试解说: {context}"


class MockTTSProvider(TTSProvider):
    """模拟文本转语音 Provider"""

    def synthesize(self, text: str, voice: str | None = None) -> AudioData:
        return AudioData(
            audio_bytes=b"fake_audio_data",
            duration_ms=3000,
            format="mp3",
        )

    def synthesize_with_timing(self, text: str, word_timings: list[float]) -> AudioData:
        return AudioData(
            audio_bytes=b"fake_timed_audio",
            duration_ms=len(word_timings) * 500,
            format="mp3",
        )


# =============================================================================
# Tests
# =============================================================================

class TestProviderRegistrySingleton:
    """测试单例模式"""

    def test_instance_returns_same_instance(self):
        """测试 instance() 返回同一实例"""
        # Reset singleton
        ProviderRegistry._instance = None

        r1 = ProviderRegistry.instance()
        r2 = ProviderRegistry.instance()
        assert r1 is r2

        # Clean up
        ProviderRegistry._instance = None


class TestVisionProviderRegistration:
    """测试 Vision Provider 注册与获取"""

    def setup_method(self):
        ProviderRegistry._instance = None
        self.registry = ProviderRegistry.instance()

    def test_register_vision(self):
        """测试注册 Vision Provider"""
        provider = MockVisionProvider()
        self.registry.register_vision("test_vision", provider)
        assert "test_vision" in self.registry.list_vision_providers()

    def test_get_vision_by_name(self):
        """测试按名称获取 Vision Provider"""
        provider = MockVisionProvider()
        self.registry.register_vision("qv", provider)

        retrieved = self.registry.get_vision("qv")
        assert retrieved is provider

    def test_get_vision_unknown_raises(self):
        """测试获取未知 Provider 抛出 KeyError"""
        with pytest.raises(KeyError) as exc_info:
            self.registry.get_vision("nonexistent")
        assert "nonexistent" in str(exc_info.value)

    def test_get_default_vision(self):
        """测试获取默认 Vision Provider"""
        provider = MockVisionProvider()
        self.registry.register_vision("default_vision", provider)
        self.registry.set_default_vision("default_vision")

        default = self.registry.get_default_vision()
        assert default is provider

    def test_get_default_vision_auto_first(self):
        """测试未设置默认时自动返回第一个"""
        provider = MockVisionProvider()
        self.registry.register_vision("only_vision", provider)

        default = self.registry.get_default_vision()
        assert default is provider

    def test_get_default_vision_no_provider_raises(self):
        """测试无 Provider 时抛出 RuntimeError"""
        registry = ProviderRegistry()  # fresh instance with no providers
        with pytest.raises(RuntimeError) as exc_info:
            registry.get_default_vision()
        assert "No Vision providers" in str(exc_info.value)


class TestLLMProviderRegistration:
    """测试 LLM Provider 注册与获取"""

    def setup_method(self):
        ProviderRegistry._instance = None
        self.registry = ProviderRegistry.instance()

    def test_register_llm(self):
        """测试注册 LLM Provider"""
        provider = MockLLMProvider()
        self.registry.register_llm("test_llm", provider)
        assert "test_llm" in self.registry.list_llm_providers()

    def test_get_llm_by_name(self):
        """测试按名称获取 LLM Provider"""
        provider = MockLLMProvider()
        self.registry.register_llm("my_llm", provider)

        retrieved = self.registry.get_llm("my_llm")
        assert retrieved is provider

    def test_get_llm_unknown_raises(self):
        """测试获取未知 LLM Provider 抛出 KeyError"""
        with pytest.raises(KeyError) as exc_info:
            self.registry.get_llm("unknown_llm")
        assert "unknown_llm" in str(exc_info.value)

    def test_get_default_llm(self):
        """测试获取默认 LLM Provider"""
        provider = MockLLMProvider()
        self.registry.register_llm("my_deepseek", provider)
        self.registry.set_default_llm("my_deepseek")

        default = self.registry.get_default_llm()
        assert default is provider


class TestTTSProviderRegistration:
    """测试 TTS Provider 注册与获取"""

    def setup_method(self):
        ProviderRegistry._instance = None
        self.registry = ProviderRegistry.instance()

    def test_register_tts(self):
        """测试注册 TTS Provider"""
        provider = MockTTSProvider()
        self.registry.register_tts("edge_tts", provider)
        assert "edge_tts" in self.registry.list_tts_providers()

    def test_get_tts_by_name(self):
        """测试按名称获取 TTS Provider"""
        provider = MockTTSProvider()
        self.registry.register_tts("my_tts", provider)

        retrieved = self.registry.get_tts("my_tts")
        assert retrieved is provider

    def test_get_default_tts(self):
        """测试获取默认 TTS Provider"""
        provider = MockTTSProvider()
        self.registry.register_tts("my_edge", provider)
        self.registry.set_default_tts("my_edge")

        default = self.registry.get_default_tts()
        assert default is provider


class TestProviderProtocolCompliance:
    """测试 Provider 协议合规性"""

    def test_mock_vision_provider_implements_protocol(self):
        """测试 MockVisionProvider 实现了 VisionProvider 协议"""
        provider = MockVisionProvider()
        assert isinstance(provider, VisionProvider)

    def test_mock_llm_provider_implements_protocol(self):
        """测试 MockLLMProvider 实现了 LLMProvider 协议"""
        provider = MockLLMProvider()
        assert isinstance(provider, LLMProvider)

    def test_mock_tts_provider_implements_protocol(self):
        """测试 MockTTSProvider 实现了 TTSProvider 协议"""
        provider = MockTTSProvider()
        assert isinstance(provider, TTSProvider)

    def test_vision_provider_protocol_methods(self):
        """测试 VisionProvider 协议方法"""
        provider = MockVisionProvider()

        result = provider.analyze_video("/test/video.mp4")
        assert isinstance(result, VideoAnalysis)
        assert result.summary == "测试摘要"
        assert "test" in result.tags

        frames = provider.extract_keyframes("/test/video.mp4", 3)
        assert len(frames) == 3

    def test_llm_provider_protocol_methods(self):
        """测试 LLMProvider 协议方法"""
        provider = MockLLMProvider()

        result = provider.generate_script("写一个关于AI的视频脚本", style="narrative")
        assert isinstance(result, ScriptResult)
        assert "测试脚本" in result.script
        assert result.style == "narrative"

        narration = provider.generate_narration("AI发展迅速", character="年轻女性")
        assert "测试解说" in narration

    def test_tts_provider_protocol_methods(self):
        """测试 TTSProvider 协议方法"""
        provider = MockTTSProvider()

        result = provider.synthesize("你好世界", voice="zh-CN-Xiaoxiao")
        assert isinstance(result, AudioData)
        assert result.format == "mp3"
        assert result.duration_ms == 3000

        timed = provider.synthesize_with_timing("你好世界", [0.0, 0.5, 1.0, 1.5])
        assert timed.duration_ms == 2000  # 4 words * 500ms


class TestProviderRegistryConfig:
    """测试配置文件加载"""

    def setup_method(self):
        ProviderRegistry._instance = None
        self.registry = ProviderRegistry.instance()

    def test_load_config_from_yaml(self):
        """测试从 YAML 文件加载配置"""
        config_content = """
providers:
  vision:
    default: qwen_vl
    qwen_vl:
      enabled: true
      model: Qwen2.5-VL
    gemini_vision:
      enabled: true
      model: gemini-2.0-flash

  llm:
    default: deepseek
    deepseek:
      enabled: true
      model: deepseek-chat

  tts:
    default: edge_tts
    edge_tts:
      enabled: true
      voice: zh-CN-Xiaoxiao
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            config = self.registry.load_config(temp_path)

            assert config is not None
            assert "providers" in config
            assert config["providers"]["vision"]["default"] == "qwen_vl"
            assert config["providers"]["llm"]["default"] == "deepseek"
            assert config["providers"]["tts"]["default"] == "edge_tts"

            # 检查默认设置生效
            assert self.registry._default_vision == "qwen_vl"
            assert self.registry._default_llm == "deepseek"
            assert self.registry._default_tts == "edge_tts"
        finally:
            os.unlink(temp_path)

    def test_load_config_file_not_found(self):
        """测试加载不存在的配置文件抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            self.registry.load_config("/nonexistent/path/config.yaml")

    def test_config_returns_none_when_not_loaded(self):
        """测试未加载配置时 config 属性返回 None"""
        registry = ProviderRegistry()
        assert registry.config is None


class TestProviderRegistryIntrospection:
    """测试注册表自省功能"""

    def setup_method(self):
        ProviderRegistry._instance = None
        self.registry = ProviderRegistry.instance()

    def test_list_vision_providers(self):
        """测试列出所有 Vision Provider"""
        self.registry.register_vision("v1", MockVisionProvider())
        self.registry.register_vision("v2", MockVisionProvider())

        providers = self.registry.list_vision_providers()
        assert set(providers) == {"v1", "v2"}

    def test_list_llm_providers(self):
        """测试列出所有 LLM Provider"""
        self.registry.register_llm("llm1", MockLLMProvider())
        self.registry.register_llm("llm2", MockLLMProvider())

        providers = self.registry.list_llm_providers()
        assert set(providers) == {"llm1", "llm2"}

    def test_list_tts_providers(self):
        """测试列出所有 TTS Provider"""
        self.registry.register_tts("tts1", MockTTSProvider())

        providers = self.registry.list_tts_providers()
        assert providers == ["tts1"]
