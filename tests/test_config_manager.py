#!/usr/bin/env python3
"""测试配置管理器"""

import pytest
from app.core.config_manager import (
    LLMProviderType,
    LLMConfig,
    CacheConfig,
)


class TestLLMProviderType:
    """测试 LLM 提供商类型"""

    def test_qwen(self):
        """测试 QWEN"""
        assert LLMProviderType.QWEN.value == "qwen"

    def test_kimi(self):
        """测试 KIMI"""
        assert LLMProviderType.KIMI.value == "kimi"

    def test_glm5(self):
        """测试 GLM5"""
        assert LLMProviderType.GLM5.value == "glm5"

    def test_openai(self):
        """测试 OpenAI"""
        assert LLMProviderType.OPENAI.value == "openai"


class TestLLMConfig:
    """测试 LLM 配置"""

    def test_default(self):
        """测试默认值"""
        config = LLMConfig()
        
        assert config.enabled is False
        assert config.api_key == ""
        assert config.model == ""
        assert config.temperature == 0.7
        assert config.max_tokens == 2000

    def test_is_valid_disabled(self):
        """测试禁用时无效"""
        config = LLMConfig(enabled=False)
        
        assert config.is_valid() is False

    def test_is_valid_no_api_key(self):
        """测试无 API key 时无效"""
        config = LLMConfig(enabled=True, model="test")
        
        assert config.is_valid() is False

    def test_is_valid_no_model(self):
        """测试无模型时无效"""
        config = LLMConfig(enabled=True, api_key="key")
        
        assert config.is_valid() is False

    def test_is_valid_complete(self):
        """测试完整配置有效"""
        config = LLMConfig(
            enabled=True,
            api_key="test_key",
            model="test_model"
        )
        
        assert config.is_valid() is True


class TestCacheConfig:
    """测试缓存配置"""

    def test_default(self):
        """测试默认值"""
        config = CacheConfig()
        
        assert config.enabled is True
        assert config.max_size == 100
        assert config.ttl == 3600

    def test_is_valid_enabled(self):
        """测试启用时有效"""
        config = CacheConfig(enabled=True, max_size=10, ttl=100)
        
        assert config.is_valid() is True

    def test_is_valid_disabled(self):
        """测试禁用时无效"""
        config = CacheConfig(enabled=False)
        
        assert config.is_valid() is False

    def test_is_valid_zero_max_size(self):
        """测试零大小时无效"""
        config = CacheConfig(enabled=True, max_size=0)
        
        assert config.is_valid() is False

    def test_is_valid_zero_ttl(self):
        """测试零 TTL 时无效"""
        config = CacheConfig(enabled=True, ttl=0)
        
        assert config.is_valid() is False
