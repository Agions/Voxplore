#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Gemini 提供商
支持 Gemini 3.1 Flash / Gemini 3.1 Pro (2026年4月最新)

使用公共混入类减少重复代码
"""

from typing import List
import base64
from pathlib import Path

import httpx
from ..base_llm_provider import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    HTTPClientMixin,
    ModelManagerMixin,
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

        # 构建内容 (Gemini 特殊格式)
        contents = []
        if request.system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {request.system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood."}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": request.prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
                "topP": request.top_p,
            },
        }

        try:
            response = await self.http_client.post(
                f"{self.base_url}/v1beta/models/{model}:generateContent",
                params={"key": self.api_key},
                json=payload,
            )

            data = response.json()

            if "error" in data:
                raise ProviderError(data["error"]["message"])

            # 提取内容
            candidates = data.get("candidates", [])
            if not candidates:
                raise ProviderError("No response generated")

            content_parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(part.get("text", "") for part in content_parts)

            usage = data.get("usageMetadata", {})
            tokens_used = (usage.get("promptTokenCount", 0) +
                          usage.get("candidatesTokenCount", 0))

            return LLMResponse(
                content=content,
                model=model,
                tokens_used=tokens_used,
                finish_reason=candidates[0].get("finishReason", "STOP"),
            )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def generate_with_image(
        self,
        request: LLMRequest,
        image_path: str,
    ) -> LLMResponse:
        """带图片的生成（Vision 能力）"""
        model = self._get_model_name(request.model)

        # 读取图片
        image_path = Path(image_path)
        if not image_path.exists():
            raise ProviderError(f"图片不存在: {image_path}")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # 检测图片类型
        mime_type = "image/jpeg"
        suffix = image_path.suffix.lower()
        if suffix == ".png":
            mime_type = "image/png"
        elif suffix in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif suffix == ".webp":
            mime_type = "image/webp"
        elif suffix == ".gif":
            mime_type = "image/gif"

        contents = []
        if request.system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {request.system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood."}]
            })

        contents.append({
            "role": "user",
            "parts": [
                {"inlineData": {"mimeType": mime_type, "data": image_data}},
                {"text": request.prompt},
            ]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        try:
            response = await self.http_client.post(
                f"{self.base_url}/v1beta/models/{model}:generateContent",
                params={"key": self.api_key},
                json=payload,
            )

            data = response.json()

            if "error" in data:
                raise ProviderError(data["error"]["message"])

            candidates = data.get("candidates", [])
            if not candidates:
                raise ProviderError("No response generated")

            content_parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(part.get("text", "") for part in content_parts)

            usage = data.get("usageMetadata", {})
            tokens_used = (usage.get("promptTokenCount", 0) +
                          usage.get("candidatesTokenCount", 0))

            return LLMResponse(
                content=content,
                model=model,
                tokens_used=tokens_used,
                finish_reason=candidates[0].get("finishReason", "STOP"),
            )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def generate_batch(
        self,
        requests: List[LLMRequest],
    ) -> List[LLMResponse]:
        """批量生成"""
        return await super().generate_batch(requests)

    async def close(self):
        """关闭HTTP客户端"""
        await self._close_http_client()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 需要导入httpx用于类型提示
