#!/usr/bin/env python3

"""
腾讯混元 (Hunyuan) 提供商
支持混元模型系列

使用公共混入类减少重复代码
"""

import json

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


class HunyuanProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    腾讯混元提供商

    API 文档: https://cloud.tencent.com/document/product/1729
    """

    MODELS = provider_models("hunyuan")
    DEFAULT_MODEL = DEFAULT_MODELS["hunyuan"]

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
        self._init_http_client(
            {
                "Content-Type": "application/json",
            }
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        try:
            response = await self.http_client.post(  # type: ignore[union-attr]
                "",
                json={
                    "Model": model,
                    "Messages": messages,
                    "MaxTokens": request.max_tokens or 4096,
                    "Temperature": request.temperature or 0.7,
                    "TopP": request.top_p or 0.95,
                    "Stream": 0,
                },
            )
        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except httpx.HTTPError as e:
            raise ProviderError(f"生成失败 (网络错误): {e}") from e
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ProviderError(f"生成失败 (响应解析): {e}") from e

        if response.status_code != 200:
            raise ProviderError(f"API Error: {response.status_code}")

        result = response.json()
        if "Response" in result:
            resp_data = result["Response"]
            usage_data = resp_data.get("Usage", {})
            tokens_used = usage_data.get("PromptTokens", 0) + usage_data.get(
                "CompletionTokens", 0
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

    async def generate_stream(self, request: LLMRequest):
        """流式生成"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        try:
            async with self.http_client.stream(  # type: ignore[union-attr]
                "POST",
                "",
                json={
                    "Model": model,
                    "Messages": messages,
                    "MaxTokens": request.max_tokens or 4096,
                    "Temperature": request.temperature or 0.7,
                    "Stream": 1,
                },
            ) as response:
                response.raise_for_status()
                async for data in self._iter_json_stream_payloads(response, sse=False):
                    choices = data.get("Choices", [])
                    if choices:
                        delta = choices[0].get("Delta", {})
                        if "Content" in delta:
                            yield delta["Content"]
        except Exception as e:
            raise self._stream_provider_error(e)
