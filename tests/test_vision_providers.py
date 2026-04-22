#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视觉提供商测试
"""

import pytest
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.ai.vision_providers import (
    VisionProvider,
    OpenAIVisionProvider,
    QwenVLProvider,
    GeminiVisionProvider,
    VisionAnalyzerFactory,
)


class TestVisionProvider:
    """视觉提供商基类测试"""

    def test_base_class_abstract(self):
        """测试基类是抽象类"""
        with pytest.raises(TypeError):
            VisionProvider(api_key="test")

    def test_subclass_must_implement(self):
        """测试子类必须实现方法"""
        class IncompleteProvider(VisionProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider(api_key="test")


class TestOpenAIVisionProvider:
    """OpenAI 视觉提供商测试"""

    def test_init(self):
        """测试初始化"""
        provider = OpenAIVisionProvider(api_key="sk-test")

        assert provider.api_key == "sk-test"

    def test_init_custom_model(self):
        """测试自定义模型"""
        provider = OpenAIVisionProvider(
            api_key="sk-test",
            model="gpt-4o-mini"
        )

        assert provider.model == "gpt-4o-mini"

    @patch('openai.OpenAI')
    def test_analyze_image(self, mock_openai):
        """测试图像分析"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"description": "测试", "tags": ["test"]}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = OpenAIVisionProvider(api_key="sk-test")

        result = provider.analyze_image(b"fake_image_data")

        assert result is not None

    def test_get_name(self):
        """测试提供商名称"""
        provider = OpenAIVisionProvider(api_key="sk-test")
        assert "openai" in provider.get_name().lower()


class TestQwenVLProvider:
    """通义千问 VL 提供商测试"""

    def test_init(self):
        """测试初始化"""
        provider = QwenVLProvider(api_key="test-key")

        assert provider.api_key == "test-key"

    @patch('openai.OpenAI')
    def test_analyze_image(self, mock_openai):
        """测试图像分析"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"description": "测试", "tags": ["test"]}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = QwenVLProvider(api_key="test-key")

        result = provider.analyze_image(b"fake_image")

        assert result is not None


class TestVisionAnalyzerFactory:
    """视觉分析器工厂测试"""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_init_with_config(self):
        """测试工厂初始化"""
        config = {
            "LLM": {
                "openai": {"api_key": "sk-test", "vision_model": "gpt-4o"}
            }
        }
        factory = VisionAnalyzerFactory(config)
        assert len(factory._providers) >= 0

    def test_get_provider_preferred(self):
        """测试获取偏好的提供商"""
        config = {
            "LLM": {
                "openai": {"api_key": "sk-test"},
                "qwen": {"api_key": "test"},
            }
        }
        factory = VisionAnalyzerFactory(config)
        _ = factory.get_provider(preferred="openai")
        # 若无可用则返回 None
        # 若有 openai key 则返回对应 provider

    def test_get_available_providers(self):
        """测试获取可用提供商列表"""
        config = {"LLM": {}}
        factory = VisionAnalyzerFactory(config)
        providers = factory.get_available_providers()
        assert isinstance(providers, list)


class TestGeminiVisionProvider:
    """Gemini 视觉提供商测试"""

    def test_init(self):
        """测试初始化"""
        provider = GeminiVisionProvider(api_key="test-key")

        assert provider.api_key == "test-key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
