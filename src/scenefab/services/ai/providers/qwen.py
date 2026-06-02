#!/usr/bin/env python3

"""
通义千问 Qwen 提供商
支持 Qwen Plus/Max/Turbo 等模型 (2026.03 最新)

优化:
- 重试机制 (RetryHandler) ✅
- 延迟统计 ✅
"""

import logging
import time

import httpx

from ..base_llm_provider import (
    BaseLLMProvider,
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
    ProviderError,
)

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
        """生成文本"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        start_time = time.monotonic()
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        async def _call():
            return await self._call_api(
                "POST", f"{self.base_url}/chat/completions", json=payload
            )

        try:
            data = await self._retry_handler.execute(_call)
            latency_ms = (time.monotonic() - start_time) * 1000
            return self._parse_response(data, model, latency_ms)
        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")


# 添加日志记录器
