#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kimi (月之暗面 Moonshot AI) 提供商
支持 moonshot-v1 系列模型 (2026.03 最新)

使用公共混入类减少重复代码
"""

from typing import List

import httpx
from ..base_llm_provider import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    HTTPClientMixin,
    ModelManagerMixin,
)


class KimiProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    Kimi 提供商

    API 文档: https://platform.moonshot.cn/docs
    """

    # 模型管理混入需要
    MODELS = {
        "moonshot-v1-128k": {
            "name": "Kimi 128K",
            "description": "超长上下文，128K tokens",
            "max_tokens": 8000,
            "context_length": 128000,
            "vision": False,
        },
        "moonshot-v1-32k": {
            "name": "Kimi 32K",
            "description": "均衡版本，32K tokens",
            "max_tokens": 8000,
            "context_length": 32000,
        },
        "moonshot-v1-8k": {
            "name": "Kimi 8K",
            "description": "标准版本，8K tokens",
            "max_tokens": 4000,
            "context_length": 8000,
        },
    }
    DEFAULT_MODEL = "moonshot-v1-128k"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.moonshot.cn/v1",
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

        # 使用混入类的方法构建消息
        messages = self._build_messages(request)

        try:
            response = await self.http_client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                },
            )

            data = response.json()
            # 使用混入类的方法解析响应
            return self._parse_response(data, model)

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def generate_batch(
        self,
        requests: List[LLMRequest],
    ) -> List[LLMResponse]:
        """批量生成"""
        return await super().generate_batch(requests)

    async def close(self):
        """关闭HTTP客户端"""
        await self._close_http_client()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 需要导入httpx用于类型提示
