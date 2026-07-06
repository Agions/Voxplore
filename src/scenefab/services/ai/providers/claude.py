#!/usr/bin/env python3

"""
Anthropic Claude 提供商
支持 Claude Sonnet 4.5

使用公共混入类减少重复代码
"""

import base64
from pathlib import Path

from ..base_llm_provider import (
    BaseLLMProvider,
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
    ProviderError,
)
from ..model_catalog import DEFAULT_MODELS, provider_models


class ClaudeProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    Anthropic Claude 提供商

    API 文档: https://docs.anthropic.com/claude/reference/messages_post
    """

    MODELS = provider_models("claude")
    DEFAULT_MODEL = DEFAULT_MODELS["claude"]

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=120.0)

        # Claude 有特殊的请求头
        self._init_http_client(
            {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2025-01-01",
            }
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)

        messages = [
            {"role": "user", "content": [{"type": "text", "text": request.prompt}]}
        ]

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt

        data = await self._call_api(
            "POST", f"{self.base_url}/v1/messages", json=payload
        )

        return self._parse_anthropic_response(data, model)

    async def generate_with_image(
        self,
        request: LLMRequest,
        image_path: str,
    ) -> LLMResponse:
        """带图片的生成（Vision 能力）"""
        model = self._get_model_name(request.model)

        image_path = Path(image_path)  # type: ignore[assignment]
        if not image_path.exists():  # type: ignore[attr-defined]
            raise ProviderError(f"图片不存在: {image_path}")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        mime_type = "image/jpeg"
        if image_path.suffix.lower() == ".png":  # type: ignore[attr-defined]
            mime_type = "image/png"
        elif image_path.suffix.lower() in [".jpg", ".jpeg"]:  # type: ignore[attr-defined]
            mime_type = "image/jpeg"
        elif image_path.suffix.lower() == ".webp":  # type: ignore[attr-defined]
            mime_type = "image/webp"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": request.prompt},
                ],
            }
        ]

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt

        data = await self._call_api(
            "POST", f"{self.base_url}/v1/messages", json=payload
        )

        return self._parse_anthropic_response(data, model)

    @staticmethod
    def _parse_anthropic_response(data: dict, model: str) -> "LLMResponse":
        """解析 Anthropic Messages API 响应（generate/generate_with_image 共享）"""
        if "error" in data:
            raise ProviderError(data["error"]["message"])

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        return LLMResponse(
            content=content,
            model=model,
            tokens_used=data.get("usage", {}).get("input_tokens", 0)
            + data.get("usage", {}).get("output_tokens", 0),
            finish_reason=data.get("stop_reason", "stop"),
        )
