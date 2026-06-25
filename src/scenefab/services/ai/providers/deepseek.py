#!/usr/bin/env python3

"""
DeepSeek 提供商
支持 DeepSeek R1, V4 Flash/Pro 系列模型
"""

import json
from collections.abc import AsyncIterator

import httpx

from ..base_llm_provider import LLMRequest, LLMResponse, ProviderError
from ..model_catalog import DEFAULT_MODELS, provider_models
from .openai_compat import OpenAICompatProvider


class DeepSeekProvider(OpenAICompatProvider):
    """
    DeepSeek 提供商（OpenAI 兼容 API + reasoning model 支持）

    API 文档: https://platform.deepseek.com/docs
    """

    PROVIDER_NAME = "deepseek"
    DEFAULT_BASE_URL = "https://api.deepseek.com"
    MODELS = provider_models("deepseek")
    DEFAULT_MODEL = DEFAULT_MODELS["deepseek"]

    def _build_request_body(self, request, model, messages):
        """构建请求体（reasoning model 启用 thinking 参数）"""
        body = super()._build_request_body(request, model, messages)
        if self._is_reasoning_model(model):
            body["thinking"] = {"type": "enabled"}
        return body

    def _is_reasoning_model(self, model: str) -> bool:
        """检查是否是推理模型"""
        model_info = self.MODELS.get(model, {})
        return model_info.get("reasoning", False)  # type: ignore[no-any-return]

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本（支持 reasoning model）"""
        model = self._get_model_name(request.model)
        is_reasoning = self._is_reasoning_model(model)
        messages = self._build_messages(request)
        body = self._build_request_body(request, model, messages)

        data = await self._call_api(
            "POST", f"{self.base_url}/chat/completions", json=body
        )
        result = self._parse_response(data, model)
        if is_reasoning:
            raw = result.raw_response or {}
            raw["is_reasoning_model"] = True
            result.raw_response = raw
        return result

    async def stream_generate(
        self,
        request: LLMRequest,
    ) -> AsyncIterator[dict]:
        """流式生成文本（支持 SSE）"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)

        api_request = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        try:
            async with self.http_client.stream(  # type: ignore[union-attr]
                "POST",
                f"{self.base_url}/chat/completions",
                json=api_request,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        yield {"done": True, "content": ""}
                        return
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield {"done": False, "content": content}
        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except httpx.HTTPError as e:
            raise ProviderError(f"流式生成失败 (网络错误): {e}") from e
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ProviderError(f"流式生成失败 (响应解析): {e}") from e

    async def count_tokens(self, text: str) -> int:
        """计算 token 数量（估算）"""
        chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
