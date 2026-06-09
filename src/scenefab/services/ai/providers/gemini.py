#!/usr/bin/env python3

"""
Google Gemini 提供商
支持 Gemini 3.1 Flash / Gemini 3.1 Pro

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


class GeminiProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    Google Gemini 提供商

    API 文档: https://ai.google.dev/docs
    """

    # 模型管理混入需要
    MODELS = {
        "gemini-3.1-flash-lite": {
            "name": "Gemini 3.1 Flash Lite",
            "description": "低成本高效模型 (2026.03)",
            "max_tokens": 8192,
            "context_length": 1000000,
            "vision": True,
        },
        "gemini-3.1-flash": {
            "name": "Gemini 3.1 Flash",
            "description": "闪电般速度 (2026.03)",
            "max_tokens": 8192,
            "context_length": 1000000,
            "vision": True,
        },
        "gemini-3.1-pro": {
            "name": "Gemini 3.1 Pro",
            "description": "最智能模型 (2026.03)",
            "max_tokens": 8192,
            "context_length": 2000000,
            "vision": True,
        },
    }
    DEFAULT_MODEL = "gemini-3.1-flash-lite"

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

        contents = []
        if request.system_prompt:
            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": f"System: {request.system_prompt}"}],
                }
            )
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": request.prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
                "topP": request.top_p,
            },
        }

        data = await self._call_api(
            "POST",
            f"{self.base_url}/v1beta/models/{model}:generateContent",
            params={"key": self.api_key},
            json=payload,
        )

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

        image_data = self._read_image_as_base64(image_path)
        mime_type = self._detect_image_mime(image_path)
        contents = self._build_multimodal_contents(request, image_data, mime_type)

        data = await self._call_api(
            "POST",
            f"{self.base_url}/v1beta/models/{model}:generateContent",
            params={"key": self.api_key},
            json=self._build_gemini_payload(request, contents),
        )

        return self._parse_gemini_response(data, model)

    @staticmethod
    def _read_image_as_base64(image_path) -> str:
        """读取图片并 base64 编码"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _detect_image_mime(image_path) -> str:
        """根据文件后缀检测 MIME 类型"""
        suffix = image_path.suffix.lower()  # type: ignore[attr-defined]
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return mime_map.get(suffix, "image/jpeg")

    @staticmethod
    def _build_multimodal_contents(
        request: LLMRequest, image_data: str, mime_type: str
    ) -> list[dict]:
        """构建多模态 contents 列表 — 系统提示 + 图片 + 文本"""
        contents = []
        if request.system_prompt:
            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": f"System: {request.system_prompt}"}],
                }
            )
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})

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
