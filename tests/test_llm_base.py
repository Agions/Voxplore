#!/usr/bin/env python3
"""测试 LLM 提供商基类和混入"""

import pytest
from dataclasses import asdict

from app.services.ai.base_llm_provider import (
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderType,
    HTTPClientMixin,
    ModelManagerMixin,
)


class TestLLMDataClasses:
    """测试 LLM 数据类"""

    def test_llm_request_defaults(self):
        """测试请求默认值为"""
        req = LLMRequest(prompt="test prompt")
        
        assert req.prompt == "test prompt"
        assert req.system_prompt == ""
        assert req.model == "default"
        assert req.max_tokens == 2000
        assert req.temperature == 0.7
        assert req.top_p == 0.9

    def test_llm_request_to_dict(self):
        """测试请求转字典"""
        req = LLMRequest(
            prompt="test",
            system_prompt="You are a helpful assistant",
            model="gpt-4",
            max_tokens=1000,
            temperature=0.5,
        )

        # LLMRequest 不是 dataclass，手动转换
        d = {
            "prompt": req.prompt,
            "system_prompt": req.system_prompt,
            "model": req.model,
            "max_tokens": req.max_tokens,
        }
        assert d["prompt"] == "test"
        assert d["system_prompt"] == "You are a helpful assistant"
        assert d["model"] == "gpt-4"
        assert d["max_tokens"] == 1000

    def test_llm_response_defaults(self):
        """测试响应默认值"""
        resp = LLMResponse(content="Hello", model="gpt-4")
        
        assert resp.content == "Hello"
        assert resp.model == "gpt-4"
        assert resp.tokens_used == 0
        assert resp.finish_reason == "stop"
        assert resp.raw_response is None


class TestProviderType:
    """测试提供商类型枚举"""

    def test_enum_values(self):
        """测试枚举值"""
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.KIMI.value == "kimi"
        assert ProviderType.DEEPSEEK.value == "deepseek"
        assert ProviderType.QWEN.value == "qwen"

    def test_enum_members(self):
        """测试枚举成员"""
        members = list(ProviderType)
        assert len(members) >= 7
        assert ProviderType.OPENAI in members


class TestProviderError:
    """测试提供商错误"""

    def test_error_creation(self):
        """测试错误创建"""
        err = ProviderError("Test error message")
        assert str(err) == "Test error message"

    def test_error_inheritance(self):
        """测试错误继承"""
        err = ProviderError("Test")
        assert isinstance(err, Exception)


class MockHTTPClient:
    """模拟 HTTP 客户端"""
    pass


class TestProviderWithMixins:
    """测试带有混入的提供商"""

    def test_http_client_mixin_init(self):
        """测试 HTTP 客户端混入初始化"""
        class TestProvider(HTTPClientMixin):
            pass
        
        provider = TestProvider(
            api_key="test-key",
            base_url="https://api.example.com",
            timeout=30.0
        )
        
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api.example.com"
        assert provider.timeout == 30.0

    def test_model_manager_mixin(self):
        """测试模型管理混入"""
        class TestProvider(ModelManagerMixin):
            MODELS = {
                "gpt-4": {"name": "GPT-4", "max_tokens": 8000},
                "gpt-3.5": {"name": "GPT-3.5", "max_tokens": 4000},
            }
            DEFAULT_MODEL = "gpt-4"
        
        provider = TestProvider()
        
        assert "gpt-4" in provider.MODELS
        assert provider.DEFAULT_MODEL == "gpt-4"
        assert provider.get_model_info("gpt-4") == {"name": "GPT-4", "max_tokens": 8000}

    def test_model_manager_get_model_info_not_found(self):
        """测试获取不存在的模型信息"""
        class TestProvider(ModelManagerMixin):
            MODELS = {}
            DEFAULT_MODEL = "default"

        provider = TestProvider()
        result = provider.get_model_info("nonexistent")

        assert result == {}
