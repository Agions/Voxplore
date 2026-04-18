#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通义千问 Qwen 提供商
支持 Qwen Plus/Max/Turbo 等模型 (2026.03 最新)

优化:
- asyncio.gather 批量并发处理 ✅
- 重试机制 (RetryHandler) ✅
- 延迟统计 ✅
"""

import time
import httpx
from typing import List

from ..base_llm_provider import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    HTTPClientMixin,
    ModelManagerMixin,
    gather_with_concurrency,
)


import logging
logger = logging.getLogger(__name__)
class QwenProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    通义千问提供商

    API 文档: https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope
    """

    # 模型管理混入需要
    MODELS = {
        "qwen-plus": {
            "name": "Qwen Plus",
            "description": "综合最佳模型，32K context",
            "max_tokens": 8000,
            "context_length": 32000,
        },
        "qwen-max": {
            "name": "Qwen Max",
            "description": "最强性能模型，128K context",
            "max_tokens": 8000,
            "context_length": 128000,
        },
        "qwen-turbo": {
            "name": "Qwen Turbo",
            "description": "高性价比，响应最快",
            "max_tokens": 6000,
            "context_length": 32000,
        },
        "qwq-32b": {
            "name": "QwQ 32B",
            "description": "推理能力模型",
            "max_tokens": 32768,
            "context_length": 32768,
            "reasoning": True,
        },
        "qwen-vl-plus": {
            "name": "Qwen VL Plus",
            "description": "视觉理解版本",
            "max_tokens": 8000,
            "context_length": 32000,
            "vision": True,
        },
    }
    DEFAULT_MODEL = "qwen-plus"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
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

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        生成文本

        Args:
            request: LLM 请求

        Returns:
            LLM 响应
        """
        model = self._get_model_name(request.model)

        # 使用混入类的方法构建消息
        messages = self._build_messages(request)

        # 调用 API（带重试机制）
        start_time = time.monotonic()
        try:
            async def _call_api():
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
                return response.json()
            
            data = await self._retry_handler.execute(_call_api)
            latency_ms = (time.monotonic() - start_time) * 1000

            # 使用混入类的方法解析响应
            return self._parse_response(data, model, latency_ms)

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def generate_batch(
        self,
        requests: List[LLMRequest],
        max_concurrency: int = 5
    ) -> List[LLMResponse]:
        """
        批量生成文本 ✅ 优化：使用 asyncio.gather 并发处理

        Args:
            requests: LLM 请求列表
            max_concurrency: 最大并发数（防止超出 API 限制）

        Returns:
            LLM 响应列表
        """
        if not requests:
            return []
        
        # 使用 gather_with_concurrency 控制并发数
        results = await gather_with_concurrency(
            max_concurrency,
            *[self.generate(req) for req in requests]
        )
        
        # 处理异常
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量请求 {i} 失败: {result}")
                # 返回错误响应而非抛出异常
                responses.append(LLMResponse(
                    content="",
                    model=requests[i].model,
                    tokens_used=0,
                    finish_reason="error",
                    raw_response={"error": str(result)}
                ))
            else:
                responses.append(result)
        
        return responses

    async def close(self):
        """关闭 HTTP 客户端"""
        await self._close_http_client()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 添加日志记录器
