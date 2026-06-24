#!/usr/bin/env python3

"""
OpenAI 兼容 API 统一基类

所有使用 OpenAI 格式 API 的 Provider（GLM5、Kimi、Qwen、Doubao、DeepSeek 等）
应继承此类，仅覆写有差异的部分。

用法::

    class GLM5Provider(OpenAICompatProvider):
        PROVIDER_NAME = "glm5"
        DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
        MODELS = provider_models("glm5")
        DEFAULT_MODEL = DEFAULT_MODELS["glm5"]
"""

from __future__ import annotations

from typing import Any

from ..base_llm_provider import (
    BaseLLMProvider,
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
)


class OpenAICompatProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    OpenAI 兼容 API 的统一基类。

    子类只需定义：
    - PROVIDER_NAME: Provider 名称（如 "glm5", "kimi"）
    - DEFAULT_BASE_URL: 默认 API 地址
    - MODELS: 可用模型字典
    - DEFAULT_MODEL: 默认模型名称

    可选覆写：
    - generate(): 自定义请求逻辑（如 DeepSeek 的 reasoning model）
    - _build_request_body(): 自定义请求体
    - _build_headers(): 自定义请求头
    """

    PROVIDER_NAME: str = ""
    DEFAULT_BASE_URL: str = ""
    DEFAULT_TIMEOUT: float = 60.0

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        url = base_url or self.DEFAULT_BASE_URL
        t = timeout or self.DEFAULT_TIMEOUT
        BaseLLMProvider.__init__(self, api_key, url)
        HTTPClientMixin.__init__(self, api_key, url, timeout=t)
        self._init_http_client(self._build_headers(api_key))

    def _build_headers(self, api_key: str) -> dict[str, str]:
        """构建请求头（子类可覆写，如 Claude 用 x-api-key）"""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _build_request_body(
        self, request: LLMRequest, model: str, messages: list[dict[str, str]]
    ) -> dict[str, Any]:
        """构建请求体（子类可覆写，如 DeepSeek 加 thinking 参数）"""
        return {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本（使用 OpenAI 兼容 API）"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)
        return await self._generate_openai_compatible(
            request=request,
            model=model,
            messages=messages,
            endpoint="/chat/completions",
        )
