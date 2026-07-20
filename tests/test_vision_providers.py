#!/usr/bin/env python3

"""
视觉提供商测试
"""

from unittest.mock import Mock, patch

import pytest

from scenefab.services.ai.vision_providers import (
    GeminiVisionProvider,
    OpenAIVisionProvider,
    VisionProvider,
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
        provider = OpenAIVisionProvider(api_key="sk-test", model="gpt-5-mini")

        assert provider.model == "gpt-5-mini"

    @patch("openai.OpenAI")
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


class TestGeminiVisionProvider:
    """Gemini 视觉提供商测试"""

    def test_init(self):
        """测试初始化"""
        provider = GeminiVisionProvider(api_key="test-key")

        assert provider.api_key == "test-key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
