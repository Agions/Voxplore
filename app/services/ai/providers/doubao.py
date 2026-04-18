#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字节豆包 (Doubao) 提供商
支持豆包模型系列 (2026年3月最新)

使用公共混入类减少重复代码
"""

import json

from ..base_llm_provider import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    HTTPClientMixin,
    ModelManagerMixin,
)


class DoubaoProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    字节豆包提供商

    API 文档: https://www.volcengine.com/docs/82379
    """

    # 模型列表 (2026年3月最新)
    MODELS = {
        "doubao-pro-32k": {
            "name": "Doubao Pro 32K",
            "description": "专业版 32K 上下文，企业级应用 (2026.03)",
            "max_tokens": 32000,
            "context_length": 32000,
        },
        "doubao-pro-128k": {
            "name": "Doubao Pro 128K",
            "description": "专业版 128K 上下文，超长文本处理 (2026.03)",
            "max_tokens": 64000,
            "context_length": 128000,
        },
        "doubao-lite-32k": {
            "name": "Doubao Lite 32K",
            "description": "轻量版 32K，性价比高 (2026.03)",
            "max_tokens": 16000,
            "context_length": 32000,
        },
        "doubao-lite-128k": {
            "name": "Doubao Lite 128K",
            "description": "轻量版 128K，超长上下文 (2026.03)",
            "max_tokens": 32000,
            "context_length": 128000,
        },
        "doubao-vision-pro": {
            "name": "Doubao Vision Pro",
            "description": "多模态版本，支持图像理解 (2026.02)",
            "max_tokens": 16000,
            "context_length": 32000,
            "vision": True,
        },
    }
    DEFAULT_MODEL = "doubao-pro-128k"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=60.0)

        # 初始化HTTP客户端
        self._init_http_client({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)

        # 构建消息
        messages = self._build_messages(request)

        try:
            response = await self.http_client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": request.max_tokens or 4096,
                    "temperature": request.temperature or 0.7,
                    "top_p": request.top_p,
                    "stream": False,
                }
            )

            if response.status_code != 200:
                raise ProviderError(f"API Error: {response.status_code} - {response.text}")

            result = response.json()
            usage_data = result.get("usage", {})
            tokens_used = (
                usage_data.get("prompt_tokens", 0) +
                usage_data.get("completion_tokens", 0)
            )

            return LLMResponse(
                content=result["choices"][0]["message"]["content"],
                model=model,
                tokens_used=tokens_used,
                finish_reason=result["choices"][0].get("finish_reason", "stop"),
                usage=usage_data or None,
                raw_response=result,
            )

        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def generate_stream(self, request: LLMRequest):
        """流式生成"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        try:
            response = await self.http_client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": request.max_tokens or 4096,
                    "temperature": request.temperature or 0.7,
                    "stream": True,
                },
                stream=True
            )

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    if line.strip() == "data: [DONE]":
                        break
                    data = json.loads(line[6:])
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

        except Exception as e:
            raise ProviderError(f"流式生成失败: {str(e)}")
