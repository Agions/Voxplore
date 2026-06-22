#!/usr/bin/env python3

"""
字节豆包 (Doubao) 提供商
支持豆包模型系列

使用公共混入类减少重复代码
"""

import httpx

from ..base_llm_provider import (
    BaseLLMProvider,
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
    ProviderError,
)
from ..model_catalog import DEFAULT_MODELS, provider_models


class DoubaoProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    字节豆包提供商

    API 文档: https://www.volcengine.com/docs/82379
    """

    MODELS = provider_models("doubao")
    DEFAULT_MODEL = DEFAULT_MODELS["doubao"]

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=60.0)

        # 初始化HTTP客户端
        self._init_http_client(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        try:
            response = await self.http_client.post(  # type: ignore[union-attr]
                "/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": request.max_tokens or 4096,
                    "temperature": request.temperature or 0.7,
                    "top_p": request.top_p,
                    "stream": False,
                },
            )

            if response.status_code != 200:
                raise ProviderError(
                    f"API Error: {response.status_code} - {response.text}"
                )

            result = response.json()
        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

        usage_data = result.get("usage", {})
        tokens_used = usage_data.get("prompt_tokens", 0) + usage_data.get(
            "completion_tokens", 0
        )

        return LLMResponse(
            content=result["choices"][0]["message"]["content"],
            model=model,
            tokens_used=tokens_used,
            finish_reason=result["choices"][0].get("finish_reason", "stop"),
            usage=usage_data or None,
            raw_response=result,
        )

    async def generate_stream(self, request: LLMRequest):
        """流式生成"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        try:
            async with self.http_client.stream(  # type: ignore[union-attr]
                "POST",
                "/chat/completions",
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
