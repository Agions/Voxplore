#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试 - LLM 提供商
"""

from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ai.base_llm_provider import LLMRequest, LLMResponse


class TestLLMRequest:
    """测试 LLM 请求"""

    def test_create_request(self):
        """测试创建请求"""
        request = LLMRequest(
            prompt="测试提示词",
            max_tokens=100,
            temperature=0.5,
        )

        assert request.prompt == "测试提示词"
        assert request.max_tokens == 100
        assert request.temperature == 0.5
        assert request.system_prompt == ""
        assert request.model == "default"

    def test_request_with_system_prompt(self):
        """测试带系统提示词的请求"""
        request = LLMRequest(
            prompt="test",
            system_prompt="You are helpful",
        )

        assert request.system_prompt == "You are helpful"


class TestLLMResponse:
    """测试 LLM 响应"""

    def test_create_response(self):
        """测试创建响应"""
        response = LLMResponse(
            content="生成的内容",
            model="qwen-plus",
            tokens_used=100,
        )

        assert response.content == "生成的内容"
        assert response.model == "qwen-plus"
        assert response.tokens_used == 100
        assert response.finish_reason == "stop"
        # metadata 字段已移除，用 raw_response 代替
        assert response.raw_response is None

    def test_response_with_metadata(self):
        """测试带原始响应的响应"""
        response = LLMResponse(
            content="content",
            model="model",
            raw_response={"key": "value"},
        )

        assert response.raw_response == {"key": "value"}
