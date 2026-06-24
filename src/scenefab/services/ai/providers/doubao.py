#!/usr/bin/env python3

"""
字节豆包 (Doubao) 提供商
支持豆包模型系列
"""


import httpx

from ..base_llm_provider import LLMRequest, ProviderError
from ..model_catalog import DEFAULT_MODELS, provider_models
from .openai_compat import OpenAICompatProvider


class DoubaoProvider(OpenAICompatProvider):
    """字节豆包提供商（OpenAI 兼容 API）"""

    PROVIDER_NAME = "doubao"
    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    MODELS = provider_models("doubao")
    DEFAULT_MODEL = DEFAULT_MODELS["doubao"]

    async def generate_stream(self, request: LLMRequest):
        """流式生成"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        try:
            async with self.http_client.stream(  # type: ignore[union-attr]
                "POST",
                f"{self.base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": request.max_tokens or 4096,
                    "temperature": request.temperature or 0.7,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for chunk in self._parse_sse_stream(response):
                    yield chunk
        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"流式生成失败: {str(e)}")
