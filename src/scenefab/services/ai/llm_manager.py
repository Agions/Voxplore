#!/usr/bin/env python3

"""
LLM 管理器
统一管理所有 LLM 提供商，支持自动切换和负载均衡
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, Self  # type: ignore[attr-defined]

from .base_llm_provider import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderType,  # 从基础模块导入
)
from .providers.claude import ClaudeProvider
from .providers.deepseek import DeepSeekProvider
from .providers.doubao import DoubaoProvider
from .providers.gemini import GeminiProvider
from .providers.glm5 import GLM5Provider
from .providers.hunyuan import HunyuanProvider
from .providers.kimi import KimiProvider
from .providers.local import LocalProvider
from .providers.qwen import QwenProvider

logger = logging.getLogger(__name__)

# Provider 注册表: (配置键名, ProviderType, 提供商类, 默认 base_url)
_PROVIDER_REGISTRY = [
    ("qwen", ProviderType.QWEN, QwenProvider, ""),
    ("kimi", ProviderType.KIMI, KimiProvider, ""),
    ("glm5", ProviderType.GLM5, GLM5Provider, ""),
    ("claude", ProviderType.CLAUDE, ClaudeProvider, "https://api.anthropic.com"),
    (
        "gemini",
        ProviderType.GEMINI,
        GeminiProvider,
        "https://generativelanguage.googleapis.com",
    ),
    ("local", ProviderType.LOCAL, LocalProvider, "http://localhost:11434"),
    ("deepseek", ProviderType.DEEPSEEK, DeepSeekProvider, "https://api.deepseek.com"),
    (
        "doubao",
        ProviderType.DOUBAO,
        DoubaoProvider,
        "https://ark.cn-beijing.volces.com/api/v3",
    ),
    (
        "hunyuan",
        ProviderType.HUNYUAN,
        HunyuanProvider,
        "https://hunyuan.tencentcloudapi.com",
    ),
]


class LLMManager:
    """
    LLM 管理器

    功能:
    1. 统一接口访问所有提供商
    2. 自动切换失败提供商
    3. 配置驱动
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.providers: dict[ProviderType, BaseLLMProvider] = {}
        self._default_provider: ProviderType | None = None
        self._init_providers()

    def _init_providers(self) -> None:
        """初始化所有提供商"""
        llm_config = self.config.get("LLM", {})

        for (
            cfg_key,
            provider_type,
            provider_cls,
            default_base_url,
        ) in _PROVIDER_REGISTRY:
            cfg = llm_config.get(cfg_key, {})
            if not cfg.get("enabled", False):
                continue
            api_key = cfg.get("api_key", "")
            if not api_key or api_key.startswith("${"):
                logger.debug(
                    f"⏭️  LLM Provider [{cfg_key}] 已启用但 API Key 未配置或为占位符"
                )
                continue
            base_url = cfg.get("base_url", default_base_url)
            self.providers[provider_type] = provider_cls(
                api_key=api_key, base_url=base_url
            )
            logger.info(f"✅ LLM Provider [{cfg_key}] 已加载")

        # 设置默认提供商
        default_name = llm_config.get("default_provider", "qwen")
        try:
            self._default_provider = ProviderType(default_name)
        except ValueError:
            if self.providers:
                self._default_provider = list(self.providers.keys())[0]
            else:
                self._default_provider = None

        if self.providers:
            logger.info(
                f"📦 LLM Manager 初始化完成，共 {len(self.providers)} 个 Provider"
            )

    async def generate(
        self,
        request: LLMRequest,
        provider: ProviderType | None = None,
    ) -> LLMResponse:
        """
        生成内容（单次）

        Args:
            request: LLM 请求
            provider: 指定提供商（可选）

        Returns:
            LLM 响应
        """
        if provider is None:
            provider = self._default_provider

        if provider not in self.providers:
            return await self._try_fallback(request, provider)

        try:
            return await self.providers[provider].generate(request)
        except Exception as e:
            logger.warning(f"Provider {provider} 生成失败: {e}")
            return await self._try_fallback(request, provider)

    async def _try_fallback(
        self,
        request: LLMRequest,
        failed_provider: ProviderType | None,
    ) -> LLMResponse:
        """尝试备用提供商"""
        for p, provider in self.providers.items():
            if p != failed_provider:
                try:
                    return await provider.generate(request)
                except Exception as e:
                    logger.warning(f"Provider {p} 也失败: {e}")
        raise ProviderError("所有 Provider 都失败")

    def get_provider(self, provider_type: ProviderType) -> BaseLLMProvider:
        """获取指定类型的 Provider"""
        return self.providers.get(provider_type)  # type: ignore[return-value]

    def get_available_providers(self) -> list[ProviderType]:
        """获取所有可用的 Provider 类型"""
        return list(self.providers.keys())

    def health_check(self) -> dict[ProviderType, bool]:
        """检查所有 Provider 健康状态"""
        return {p: provider.health_check() for p, provider in self.providers.items()}

    async def stream_generate(
        self,
        request: LLMRequest,
        provider: ProviderType | None = None,
    ) -> AsyncIterator[str]:
        """
        流式生成

        Args:
            request: LLM 请求
            provider: 指定提供商（可选）

        Yields:
            文本块
        """
        if provider is None:
            provider = self._default_provider

        if provider not in self.providers:
            logger.warning(f"Provider {provider} 不可用，尝试流式回退")
            async for chunk in self._stream_fallback(request, provider):
                yield chunk
            return

        p = self.providers[provider]
        if not hasattr(p, "stream_generate"):
            response = await p.generate(request)
            yield response.content
            return

        try:
            async for chunk in p.stream_generate(request):
                yield chunk
        except Exception as e:
            logger.warning(f"Provider {provider} 流式生成失败: {e}")
            async for chunk in self._stream_fallback(request, provider):
                yield chunk

    async def _stream_fallback(
        self,
        request: LLMRequest,
        failed_provider: ProviderType | None,
    ) -> AsyncIterator[str]:
        """流式回退"""
        for p in self.providers:
            if p != failed_provider:
                try:
                    prov = self.providers[p]
                    if hasattr(prov, "stream_generate"):
                        async for chunk in prov.stream_generate(request):
                            yield chunk
                    else:
                        resp = await prov.generate(request)
                        yield resp.content
                    return
                except Exception as e:
                    logger.warning(f"Provider {p} 流式也失败: {e}")
        raise ProviderError("所有 Provider 流式都失败")

    async def close_all(self) -> None:
        """关闭所有 Provider 连接"""
        for provider in self.providers.values():
            await provider.close()

    def generate_sync(
        self, request: LLMRequest, provider: ProviderType | None = None
    ) -> LLMResponse:
        """同步生成（内部使用）"""
        import asyncio

        return asyncio.run(self.generate(request, provider))

    def ask(
        self, question: str, context: str = "", provider: ProviderType | None = None
    ) -> str:
        """快捷方法：简单问答"""
        request = LLMRequest(
            prompt=question,
            system_prompt=f"你是一个有帮助的AI助手。{context}"
            if context
            else "你是一个有帮助的AI助手。",
            model="",
            max_tokens=2048,
            temperature=0.7,
        )
        response = self.generate_sync(request, provider)
        return response.content

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        await self.close_all()


def load_llm_config(config_file: str = "config/llm.yaml") -> dict[str, Any]:
    """加载 LLM 配置"""
    import yaml

    try:
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config or {}
    except FileNotFoundError:
        logger.warning(f"LLM 配置文件 {config_file} 不存在，使用空配置")
        return {}
