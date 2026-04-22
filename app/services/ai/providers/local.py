#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
本地 LLM 提供商
支持 Ollama、LM Studio、llama.cpp 等本地推理服务

使用公共混入类减少重复代码
"""

import httpx
from typing import List, Dict, Any

from ..base_llm_provider import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    HTTPClientMixin,
    ModelManagerMixin,
    DEFAULT_LOCAL_TIMEOUT,
)


class LocalProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    本地 LLM 提供商

    支持:
    - Ollama (http://localhost:11434)
    - LM Studio (http://localhost:1234)
    - llama.cpp server (http://localhost:8080)
    - 其他 OpenAI 兼容的本地服务
    """

    # 模型列表
    MODELS = {
        "llama3.2": {
            "name": "Llama 3.2",
            "description": "Meta Llama 3.2 (Ollama)",
            "max_tokens": 4096,
            "context_length": 128000,
        },
        "qwen2.5": {
            "name": "Qwen 2.5",
            "description": "阿里通义千问 2.5 (Ollama)",
            "max_tokens": 4096,
            "context_length": 128000,
        },
        "deepseek-r1": {
            "name": "DeepSeek-R1",
            "description": "DeepSeek 推理模型 (Ollama)",
            "max_tokens": 4096,
            "context_length": 128000,
        },
        "phi4": {
            "name": "Phi-4",
            "description": "Microsoft Phi-4 (Ollama)",
            "max_tokens": 4096,
            "context_length": 16000,
        },
    }
    DEFAULT_MODEL = "llama3.2"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "http://localhost:11434",
        backend: str = "ollama",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=DEFAULT_LOCAL_TIMEOUT)

        self.backend = backend.lower()

        # 初始化HTTP客户端
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._init_http_client(headers)

    def _get_model_name(self, model: str) -> str:
        """获取模型实际名称"""
        if model == "default":
            defaults = {
                "ollama": "llama3.2",
                "lmstudio": "local-model",
                "llamacpp": "local-model",
                "openai-compatible": "local-model",
            }
            return defaults.get(self.backend, "llama3.2")
        return model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)

        # 根据后端类型选择不同的 API 格式
        if self.backend == "ollama":
            return await self._generate_ollama(request, model)
        elif self.backend in ["lmstudio", "openai-compatible"]:
            return await self._generate_openai_compatible(request, model)
        elif self.backend == "llamacpp":
            return await self._generate_llamacpp(request, model)
        else:
            return await self._generate_ollama(request, model)

    async def _generate_ollama(self, request: LLMRequest, model: str) -> LLMResponse:
        """使用 Ollama API 生成"""
        prompt = request.prompt
        if request.system_prompt:
            prompt = f"{request.system_prompt}\n\n{prompt}"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens,
            },
        }

        try:
            response = await self.http_client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )

            data = response.json()

            if "error" in data:
                raise ProviderError(data["error"])

            return LLMResponse(
                content=data.get("response", ""),
                model=model,
                tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                finish_reason="stop",
            )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def _generate_openai_compatible(self, request: LLMRequest, model: str) -> LLMResponse:
        """使用 OpenAI 兼容 API 生成"""
        messages = self._build_messages(request)

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        try:
            response = await self.http_client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )

            data = response.json()
            return self._parse_response(data, model)

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def _generate_llamacpp(self, request: LLMRequest, model: str) -> LLMResponse:
        """使用 llama.cpp server API 生成"""
        prompt = request.prompt
        if request.system_prompt:
            prompt = f"System: {request.system_prompt}\nUser: {prompt}\nAssistant:"
        else:
            prompt = f"User: {prompt}\nAssistant:"

        payload = {
            "prompt": prompt,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "n_predict": request.max_tokens,
            "stream": False,
        }

        try:
            response = await self.http_client.post(
                f"{self.base_url}/completion",
                json=payload,
            )

            data = response.json()

            if "error" in data:
                raise ProviderError(data["error"])

            return LLMResponse(
                content=data.get("content", ""),
                model=model,
                tokens_used=data.get("tokens_evaluated", 0) + data.get("tokens_predicted", 0),
                finish_reason="stop",
            )

        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e)
        except Exception as e:
            raise ProviderError(f"生成失败: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """列出本地可用的模型"""
        if self.backend == "ollama":
            try:
                response = await self.http_client.get(f"{self.base_url}/api/tags")
                data = response.json()
                models = data.get("models", [])
                return [
                    {"name": m.get("name"), "size": m.get("size"), "modified_at": m.get("modified_at")}
                    for m in models
                ]
            except Exception as e:
                raise ProviderError(f"获取模型列表失败: {str(e)}")
        else:
            return [{"name": name, "description": info["description"]}
                    for name, info in self.MODELS.items()]

    async def pull_model(self, model: str) -> bool:
        """拉取模型（仅 Ollama）"""
        if self.backend != "ollama":
            raise ProviderError("仅 Ollama 支持拉取模型")

        try:
            response = await self.http_client.post(
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": False},
                timeout=600.0,
            )
            return response.status_code == 200
        except Exception as e:
            raise ProviderError(f"拉取模型失败: {str(e)}")

    async def generate_batch(self, requests: List[LLMRequest]) -> List[LLMResponse]:
        """批量生成"""
        return await super().generate_batch(requests)

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return list(self.MODELS.keys())

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        return self.MODELS.get(model, {})

    async def close(self):
        """关闭HTTP客户端"""
        await self._close_http_client()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
