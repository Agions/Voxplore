#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Anthropic Claude 提供商
支持 Claude Sonnet 4.5 (2026年3月最新)

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


class ClaudeProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    Anthropic Claude 提供商

    API 文档: https://docs.anthropic.com/claude/reference/messages_post
    """

    # 模型管理混入需要
    MODELS = {
        "claude-sonnet-4-5": {
            "name": "Claude Sonnet 4.5",
            "description": "速度与智能的最佳平衡 (2026.03)",
            "max_tokens": 16384,
            "context_length": 200000,
            "vision": True,
        },
        "claude-opus-4-6": {
            "name": "Claude Opus 4.6",
            "description": "最智能模型，适合复杂任务",
            "max_tokens": 16384,
            "context_length": 200000,
            "vision": True,
        },
        "claude-haiku-4-5": {
            "name": "Claude Haiku 4.5",
            "description": "最快速模型",
            "max_tokens": 8192,
            "context_length": 200000,
            "vision": True,
        },
    }
    DEFAULT_MODEL = "claude-sonnet-4-5"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=120.0)

        # Claude 有特殊的请求头
        self._init_http_client({
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2025-01-01",
        })

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)

        # Claude 特殊格式：system参数单独传递
        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": request.prompt}]
        }]

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        try:
            response = await self.http_client.post(
                f"{self.base_url}/v1/messages",
                json=payload,
            )

            data = response.json()

            if "error" in data:
                raise ProviderError(data["error"]["message"])

            # Claude 响应格式特殊
            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")

            return LLMResponse(
                content=content,
                model=model,
                tokens_used=data.get("usage", {}).get("input_tokens", 0) +
                          data.get("usage", {}).get("output_tokens", 0),
                finish_reason=data.get("stop_reason", "stop"),
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

        # 读取图片并转为 base64
        image_path = Path(image_path)
        if not image_path.exists():
            raise ProviderError(f"图片不存在: {image_path}")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # 检测图片类型
        mime_type = "image/jpeg"
        if image_path.suffix.lower() == ".png":
            mime_type = "image/png"
        elif image_path.suffix.lower() in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif image_path.suffix.lower() == ".webp":
            mime_type = "image/webp"

        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": image_data,
                    }
                },
                {"type": "text", "text": request.prompt},
            ]
        }]

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        try:
            response = await self.http_client.post(
                f"{self.base_url}/v1/messages",
                json=payload,
            )

            data = response.json()

            if "error" in data:
                raise ProviderError(data["error"]["message"])

            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")

            return LLMResponse(
                content=content,
                model=model,
                tokens_used=data.get("usage", {}).get("input_tokens", 0) +
                          data.get("usage", {}).get("output_tokens", 0),
                finish_reason=data.get("stop_reason", "stop"),
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
