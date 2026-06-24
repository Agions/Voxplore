#!/usr/bin/env python3

"""
通义千问 Qwen 提供商
支持 Qwen Plus/Max/Turbo 等模型
"""

import logging
import time

from ..base_llm_provider import LLMRequest, LLMResponse, ProviderError
from ..model_catalog import DEFAULT_MODELS, provider_models
from .openai_compat import OpenAICompatProvider

logger = logging.getLogger(__name__)


class QwenProvider(OpenAICompatProvider):
    """
    通义千问提供商（OpenAI 兼容 API + 重试 + 延迟统计）

    API 文档: https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope
    """

    PROVIDER_NAME = "qwen"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODELS = provider_models("qwen")
    DEFAULT_MODEL = DEFAULT_MODELS["qwen"]

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本（带重试和延迟统计）"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)
        body = self._build_request_body(request, model, messages)

        start_time = time.monotonic()

        async def _call():
            return await self._call_api(
                "POST", f"{self.base_url}/chat/completions", json=body
            )

        try:
            data = await self._retry_handler.execute(_call)
            latency_ms = (time.monotonic() - start_time) * 1000
            return self._parse_response(data, model, latency_ms)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")
