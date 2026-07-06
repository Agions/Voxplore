#!/usr/bin/env python3

"""
Google Gemini 提供商
支持 Gemini 3.1 Flash / Gemini 3.1 Pro

使用公共混入类减少重复代码
"""

from ..base_llm_provider import (
    BaseLLMProvider,
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
    ProviderError,
)
from ..model_catalog import DEFAULT_MODELS, provider_models
from ..vision_base import VisionProvider


class GeminiProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    Google Gemini 提供商

    API 文档: https://ai.google.dev/docs
    """

    MODELS = provider_models("gemini")
    DEFAULT_MODEL = DEFAULT_MODELS["gemini"]

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=120.0)

        # 初始化HTTP客户端
        self._init_http_client()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)

        contents = GeminiProvider._add_system_prompt_to_contents(contents=[], request=request)
        contents.append({"role": "user", "parts": [{"text": request.prompt}]})

        payload = self._build_gemini_payload(request, contents)

        data = await self._call_api(
            "POST",
            f"{self.base_url}/v1beta/models/{model}:generateContent",
            params={"key": self.api_key},
            json=payload,
        )

        return self._parse_gemini_response(data, model)

    async def generate_with_image(
        self,
        request: LLMRequest,
        image_path: str,
    ) -> LLMResponse:
        """带图片的生成（Vision 能力）"""
        model = self._get_model_name(request.model)
        image_data = VisionProvider.read_image_as_base64(image_path)
        mime_type = VisionProvider.detect_image_mime(image_path)
        contents = self._build_multimodal_contents(request, image_data, mime_type)

        data = await self._call_api(
            "POST",
            f"{self.base_url}/v1beta/models/{model}:generateContent",
            params={"key": self.api_key},
            json=self._build_gemini_payload(request, contents),
        )

        return self._parse_gemini_response(data, model)

    @staticmethod
    def _add_system_prompt_to_contents(
        contents: list, request: LLMRequest
    ) -> list:
        """如果 request 有 system_prompt, 追加 system + model acknowledgment 到 contents.

        generate() 和 _build_multimodal_contents() 都用此模式.
        返回 contents（mutated in place 但也返回, 方便链式用法）.
        """
        if request.system_prompt:
            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": f"System: {request.system_prompt}"}],
                }
            )
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        return contents

    @staticmethod
    def _build_multimodal_contents(
        request: LLMRequest, image_data: str, mime_type: str
    ) -> list[dict]:
        """构建多模态 contents 列表 — 系统提示 + 图片 + 文本"""
        contents = GeminiProvider._add_system_prompt_to_contents(
            contents=[], request=request
        )

        contents.append(
            {
                "role": "user",
                "parts": [
                    {"inlineData": {"mimeType": mime_type, "data": image_data}},
                    {"text": request.prompt},
                ],
            }
        )
        return contents

    @staticmethod
    def _build_gemini_payload(request: LLMRequest, contents: list[dict]) -> dict:
        """构建 Gemini API payload"""
        return {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }

    @staticmethod
    def _parse_gemini_response(data: dict, model: str) -> "LLMResponse":
        """解析 Gemini API 响应"""
        if "error" in data:
            raise ProviderError(data["error"]["message"])

        candidates = data.get("candidates", [])
        if not candidates:
            raise ProviderError("No response generated")

        content_parts = candidates[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in content_parts)
        usage = data.get("usageMetadata", {})
        tokens_used = usage.get("promptTokenCount", 0) + usage.get(
            "candidatesTokenCount", 0
        )

        return LLMResponse(
            content=content,
            model=model,
            tokens_used=tokens_used,
            finish_reason=candidates[0].get("finishReason", "STOP"),
        )
