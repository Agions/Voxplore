#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepSeek 提供商
支持 DeepSeek R1, V4 Flash/Pro 系列模型
"""

import json
from typing import AsyncIterator

import httpx

from ..base_llm_provider import (
    BaseLLMProvider,
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
    ProviderError,
)


class DeepSeekProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    DeepSeek 提供商

    API 文档: https://platform.deepseek.com/docs

    支持模型:
    - deepseek-reasoner (R1): 推理模型，数学和代码能力强大
    - deepseek-v3-2 (V3.2): 最新基础模型，多任务能力强
    - deepseek-chat: 通用对话模型
    """

    # 可用模型列表
    MODELS = {
        "deepseek-v4-flash": {
            "name": "DeepSeek V4 Flash",
            "description": "V4 主力模型，MoE架构，1M上下文，极高性价比 (2026.04)",
            "max_tokens": 16384,
            "context_length": 1000000,
        },
        "deepseek-v4-pro": {
            "name": "DeepSeek V4 Pro",
            "description": "V4 高配版，推理能力更强，适合复杂任务 (2026.04)",
            "max_tokens": 32768,
            "context_length": 1000000,
            "reasoning": True,
        },
        "deepseek-reasoner": {
            "name": "DeepSeek R1",
            "description": "推理模型，数学和代码能力强大，适合复杂推理任务 (2026.03)",
            "max_tokens": 32768,
            "context_length": 64000,
            "reasoning": True,
        },
        "deepseek-chat": {
            "name": "DeepSeek V3 (兼容)",
            "description": "V3.2 基础模型，多任务能力强 (2026.03)",
            "max_tokens": 16384,
            "context_length": 64000,
        },
        "deepseek-coder": {
            "name": "DeepSeek Coder",
            "description": "代码生成模型",
            "max_tokens": 4096,
            "context_length": 16000,
        },
        "deepseek-math": {
            "name": "DeepSeek Math",
            "description": "数学推理模型",
            "max_tokens": 4096,
            "context_length": 64000,
        },
    }

    # 默认模型
    DEFAULT_MODEL = "deepseek-v4-flash"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
    ):
        """
        初始化提供商

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
        """
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=60.0)

        # 初始化HTTP客户端
        self._init_http_client({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _is_reasoning_model(self, model: str) -> bool:
        """检查是否是推理模型"""
        model_info = self.MODELS.get(model, {})
        return model_info.get("reasoning", False)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)
        is_reasoning = self._is_reasoning_model(model)
        messages = self._build_messages(request)

        api_request = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        if is_reasoning:
            api_request["thinking"] = {"type": "enabled"}

        data = await self._call_api(
            "POST", f"{self.base_url}/chat/completions", json=api_request
        )
        result = self._parse_response(data, model)
        if is_reasoning:
            raw = result.raw_response or {}
            raw["is_reasoning_model"] = True
            result.raw_response = raw
        return result

    async def stream_generate(
        self,
        request: LLMRequest,
    ) -> AsyncIterator[dict]:
        """流式生成文本（支持 SSE）"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        api_request = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        try:
            async with self.http_client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=api_request,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        yield {"done": True, "content": ""}
                        return
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield {"done": False, "content": content}
        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"流式生成失败: {str(e)}")

    async def count_tokens(self, text: str) -> int:
        """计算 token 数量（估算）"""
        # 简单估算：中文约 1.5 token/字符，英文约 0.25 token/字符
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
