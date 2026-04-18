#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
腾讯混元 (Hunyuan) 提供商
支持混元模型系列 (2026年3月最新)

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


class HunyuanProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    腾讯混元提供商

    API 文档: https://cloud.tencent.com/document/product/1729
    """

    # 模型列表 (2026年3月最新)
    MODELS = {
        "hunyuan-pro": {
            "name": "Hunyuan Pro",
            "description": "专业版，腾讯最强模型 (2026.03)",
            "max_tokens": 8000,
            "context_length": 128000,
        },
        "hunyuan-standard": {
            "name": "Hunyuan Standard",
            "description": "标准版，均衡性能 (2026.03)",
            "max_tokens": 4000,
            "context_length": 64000,
        },
        "hunyuan-lite": {
            "name": "Hunyuan Lite",
            "description": "轻量版，高性价比 (2026.03)",
            "max_tokens": 2000,
            "context_length": 32000,
        },
        "hunyuan-vision": {
            "name": "Hunyuan Vision",
            "description": "多模态版本，支持图像理解 (2026.02)",
            "max_tokens": 4000,
            "context_length": 64000,
            "vision": True,
        },
    }
    DEFAULT_MODEL = "hunyuan-pro"

    def __init__(
        self,
        api_key: str,
        secret_id: str = "",
        secret_key: str = "",
        base_url: str = "https://hunyuan.tencentcloudapi.com",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        
        # 腾讯云需要特殊认证
        self.secret_id = secret_id
        self.secret_key = secret_key
        
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=60.0)

        # 初始化HTTP客户端
        self._init_http_client({
            "Content-Type": "application/json",
        })

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)

        # 构建消息
        messages = self._build_messages(request)

        try:
            # 腾讯混元使用同步API
            response = await self.http_client.post(
                "",
                json={
                    "Model": model,
                    "Messages": messages,
                    "MaxTokens": request.max_tokens or 4096,
                    "Temperature": request.temperature or 0.7,
                    "TopP": request.top_p or 0.95,
                    "Stream": 0,
                }
            )

            if response.status_code != 200:
                raise ProviderError(f"API Error: {response.status_code}")

            result = response.json()

            if "Response" in result:
                resp_data = result["Response"]
                usage_data = resp_data.get("Usage", {})
                tokens_used = (
                    usage_data.get("PromptTokens", 0) +
                    usage_data.get("CompletionTokens", 0)
                )
                return LLMResponse(
                    content=resp_data["Choices"][0]["Message"]["Content"],
                    model=model,
                    tokens_used=tokens_used,
                    finish_reason="stop",
                    usage=usage_data or None,
                    raw_response=resp_data,
                )
            else:
                raise ProviderError(f"API Error: {result}")

        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def generate_stream(self, request: LLMRequest):
        """流式生成"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        try:
            response = await self.http_client.post(
                "",
                json={
                    "Model": model,
                    "Messages": messages,
                    "MaxTokens": request.max_tokens or 4096,
                    "Temperature": request.temperature or 0.7,
                    "Stream": 1,
                },
                stream=True
            )

            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "Choices" in data:
                        delta = data["Choices"][0].get("Delta", {})
                        if "Content" in delta:
                            yield delta["Content"]

        except Exception as e:
            raise ProviderError(f"流式生成失败: {str(e)}")
