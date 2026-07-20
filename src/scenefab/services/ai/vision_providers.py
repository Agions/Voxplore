#!/usr/bin/env python3

"""
多模型视觉分析适配器
支持 Qwen3.7 (Max/Plus)、GPT-5 Vision、Gemini 3.5 Flash 等多种 Vision 模型
"""

import logging
from typing import Any

# 基类和常量从 vision_base 导入，避免循环导入
from .model_catalog import DEFAULT_MODELS
from .vision_base import (
    FIRST_PERSON_ANALYSIS_PROMPT,
    VISION_ANALYSIS_PROMPT,
    VisionProvider,
)

logger = logging.getLogger(__name__)


# ============================================================================
# OpenAI GPT-5 Vision
# ============================================================================
class OpenAIVisionProvider(VisionProvider):
    """OpenAI GPT-5 Vision"""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODELS["openai"],
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def get_name(self) -> str:
        return f"OpenAI/{self.model}"

    def analyze_image(
        self, image_base64: str, prompt: str = VISION_ANALYSIS_PROMPT
    ) -> dict[str, Any]:
        from openai import OpenAI

        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url

        client = OpenAI(**kwargs)  # type: ignore[arg-type]
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=800,
        )
        return self._parse_json_response(response.choices[0].message.content)  # type: ignore[arg-type]


# ============================================================================
# Google Gemini 3.x Vision
# ============================================================================
class GeminiVisionProvider(VisionProvider):
    """Google Gemini 3.x Vision"""

    def __init__(self, api_key: str, model: str = DEFAULT_MODELS["gemini"]) -> None:
        self.api_key = api_key
        self.model = model

    def get_name(self) -> str:
        return f"Gemini/{self.model}"

    def analyze_image(
        self, image_base64: str, prompt: str = VISION_ANALYSIS_PROMPT
    ) -> dict[str, Any]:
        import httpx

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:generateContent?key={self.api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"maxOutputTokens": 800},
        }

        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_json_response(text)
