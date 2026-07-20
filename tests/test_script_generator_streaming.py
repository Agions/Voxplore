#!/usr/bin/env python3

"""
单元测试 - 流式文案生成器
"""

from scenefab.services.ai.script_stream import StreamingScriptGenerator


class TestStreamingScriptGeneratorInit:
    """测试流式生成器初始化"""

    def test_default_init(self):
        """测试默认初始化（use_llm_manager=True）"""
        gen = StreamingScriptGenerator()
        assert gen.use_llm_manager is True
        assert gen.stream_enabled is True

    def test_stream_disabled_init(self):
        """测试禁用流式"""
        gen = StreamingScriptGenerator(stream_enabled=False)
        assert gen.stream_enabled is False

    def test_inherits_from_script_generator(self):
        """测试继承自 ScriptGenerator"""
        from scenefab.services.ai.script_generator import ScriptGenerator

        assert issubclass(StreamingScriptGenerator, ScriptGenerator)


class TestProviderStreamingSupport:
    """测试 Provider 流式支持检测"""

    def test_openai_supports_streaming(self):
        """测试 OpenAI provider 支持流式"""
        gen = StreamingScriptGenerator(use_llm_manager=True)
        assert gen._provider_supports_streaming("openai") is True

    def test_anthropic_supports_streaming(self):
        """测试 Anthropic provider 支持流式"""
        gen = StreamingScriptGenerator(use_llm_manager=True)
        assert gen._provider_supports_streaming("anthropic") is True

    def test_unknown_provider_no_streaming(self):
        """测试未知 provider 不支持流式"""
        gen = StreamingScriptGenerator(use_llm_manager=True)
        assert gen._provider_supports_streaming("unknown") is False

    def test_none_provider_no_streaming(self):
        """测试 None provider 返回 True（走 LLMManager 路径）"""
        gen = StreamingScriptGenerator(use_llm_manager=True)
        # None provider 通过 LLMManager 代理，也视为支持流式
        assert gen._provider_supports_streaming(None) is True


class TestSentimentAnalysis:
    """测试快速情感分析"""

    def test_positive_sentiment(self):
        """测试正面情感"""
        gen = StreamingScriptGenerator(use_llm_manager=True)
        score = gen._analyze_sentiment_fast("太棒了！非常开心")
        assert score > 0

    def test_negative_sentiment(self):
        """测试负面情感"""
        gen = StreamingScriptGenerator(use_llm_manager=True)
        score = gen._analyze_sentiment_fast("太糟糕了，非常难过")
        assert score < 0

    def test_neutral_sentiment(self):
        """测试中性情感"""
        gen = StreamingScriptGenerator(use_llm_manager=True)
        score = gen._analyze_sentiment_fast("这是一个普通的陈述")
        assert score == 0.0

    def test_empty_text(self):
        """测试空文本"""
        gen = StreamingScriptGenerator(use_llm_manager=True)
        score = gen._analyze_sentiment_fast("")
        assert score == 0.0


class TestModuleExports:
    """测试模块导出"""

    def test_all_exports(self):
        """测试 __all__ 导出"""
        from scenefab.services.ai import script_stream as sg_streaming

        assert "StreamingScriptGenerator" in sg_streaming.__all__

    def test_import_from_package(self):
        """测试从包级别导入"""
        from scenefab.services.ai import StreamingScriptGenerator

        assert StreamingScriptGenerator is not None
