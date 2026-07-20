#!/usr/bin/env python3

"""
流式文案生成器 (Streaming Script Generator)

支持 SSE (Server-Sent Events) 和实时输出的文案生成器。
基于 ScriptGenerator 扩展，支持流式响应。

使用示例:
    from scenefab.services.ai import StreamingScriptGenerator

    generator = StreamingScriptGenerator(use_llm_manager=True)

    # 使用回调进行流式生成
    def on_chunk(chunk: str):
        print(chunk, end='', flush=True)

    script = generator.generate_streaming(
        topic="这部电影讲述了一个感人的故事",
        on_chunk=on_chunk
    )
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from scenefab.utils.async_bridge import run_async_safely

from .script_generator import ScriptGenerator
from .script_models import (
    GeneratedScript,
    ScriptConfig,
    ScriptStyle,
)

logger = logging.getLogger(__name__)

__all__ = ["StreamingScriptGenerator"]


class StreamingScriptGenerator(ScriptGenerator):
    """
    流式文案生成器

    支持实时输出文本块的文案生成器。通过回调函数或异步迭代器
    逐块返回生成的文本，适合需要实时展示生成进度的场景。

    特性:
    - 支持 SSE (Server-Sent Events) 格式输出
    - 支持 OpenAI 兼容的流式 API
    - 自动回退: 如果提供商不支持流式， fallback 到普通生成
    - 每个 chunk 都会调用回调函数

    继承自 ScriptGenerator，可以使用相同的配置方式。
    """

    def __init__(
        self,
        api_key: str | None = None,
        use_llm_manager: bool = True,
        llm_config: dict[str, Any] | None = None,
        llm_config_file: str | None = None,
        stream_enabled: bool = True,
    ):
        """
        初始化流式文案生成器

        Args:
            api_key: OpenAI API Key（传统方式）
            use_llm_manager: 是否使用 LLMManager（新架构）
            llm_config: LLM 配置字典
            llm_config_file: LLM 配置文件路径
            stream_enabled: 是否启用流式输出（可以动态切换）
        """
        super().__init__(
            api_key=api_key,
            use_llm_manager=use_llm_manager,
            llm_config=llm_config,
            llm_config_file=llm_config_file,
        )
        self.stream_enabled = stream_enabled

    def generate_streaming(
        self,
        topic: str,
        config: ScriptConfig | None = None,
        callback: Callable[[str], None] | None = None,
        sentiment_callback: Callable[[str, float], None] | None = None,
    ) -> GeneratedScript:
        """
        流式生成文案

        通过回调函数实时返回生成的文本块。
        如果 provider 不支持流式，会 fallback 到普通生成方式。

        Args:
            topic: 主题/内容描述
            config: 生成配置
            callback: 文本块回调函数，签名: (chunk: str) -> None
                     每个新生成的文本块都会调用此函数
            sentiment_callback: 情感分析回调，签名: (text: str, sentiment: float) -> None
                              当检测到文本情感变化时调用

        Returns:
            完整的 GeneratedScript 对象

        Raises:
            ValueError: 未提供有效的 API key 或配置
        """
        config = config or ScriptConfig()

        if self.use_llm_manager and self.llm_manager is not None:
            # 使用新架构的流式生成
            return self._generate_streaming_llm_manager(
                topic, config, callback, sentiment_callback
            )
        else:
            # 传统方式或不支持流式，使用普通生成
            return self._generate_fallback_streaming(topic, config, callback)

    def _generate_streaming_llm_manager(
        self,
        topic: str,
        config: ScriptConfig,
        callback: Callable[[str], None] | None,
        sentiment_callback: Callable[[str, float], None] | None,
    ) -> GeneratedScript:
        """
        使用 LLMManager 进行流式生成

        Args:
            topic: 主题
            config: 生成配置
            callback: 文本块回调
            sentiment_callback: 情感分析回调

        Returns:
            完整的 GeneratedScript
        """
        try:

            async def _run():
                return await self._generate_streaming_async(
                    topic, config, callback, sentiment_callback
                )

            result = run_async_safely(_run)

            return result  # type: ignore[no-any-return]

        except Exception as e:
            logger.warning(f"流式生成失败，回退到普通方式: {e}")
            return self._generate_fallback_streaming(topic, config, callback)

    async def _generate_streaming_async(
        self,
        topic: str,
        config: ScriptConfig,
        callback: Callable[[str], None] | None,
        sentiment_callback: Callable[[str, float], None] | None,
    ) -> GeneratedScript:
        """
        异步流式生成（内部方法）

        Args:
            topic: 主题
            config: 生成配置
            callback: 文本块回调
            sentiment_callback: 情感分析回调

        Returns:
            完整的 GeneratedScript
        """
        request, provider_type = self._build_llm_request(topic, config)
        supports_streaming = self._provider_supports_streaming(provider_type)

        if supports_streaming and self.stream_enabled:
            full_content = ""
            last_sentiment = 0.0

            async for chunk in self._generate_stream(request, provider_type):
                if chunk:
                    full_content += chunk
                    if callback:
                        callback(chunk)
                    if sentiment_callback and len(full_content) > 10:
                        sentiment = self._analyze_sentiment_fast(full_content)
                        if abs(sentiment - last_sentiment) > 0.1:
                            sentiment_callback(chunk, sentiment)
                            last_sentiment = sentiment

            await self.llm_manager.close_all()  # type: ignore[union-attr]
            return self._parse_response(full_content, config)
        else:
            logger.info("Provider 不支持流式或流式已禁用，使用普通生成方式")
            response = await self.llm_manager.generate(request, provider=provider_type)  # type: ignore[union-attr]
            await self.llm_manager.close_all()  # type: ignore[union-attr]
            full_content = response.content
            if callback:
                callback(full_content)
            return self._parse_response(full_content, config)

    async def _generate_stream(
        self,
        request,
        provider_type: Any | None,
    ) -> AsyncIterator[str]:
        """
        异步流式生成

        Args:
            request: LLMRequest 对象
            provider_type: ProviderType 或 None

        Yields:
            文本块字符串
        """
        try:
            if hasattr(self.llm_manager, "generate_stream"):
                async for chunk in self.llm_manager.generate_stream(  # type: ignore[union-attr]
                    request, provider=provider_type
                ):
                    yield chunk
            else:
                response = await self.llm_manager.generate(  # type: ignore[union-attr]
                    request, provider=provider_type
                )
                yield response.content
        except Exception as e:
            logger.error(f"流式生成错误: {e}")
            yield ""

    def _provider_supports_streaming(self, provider_type: Any | None) -> bool:
        """检查 provider 是否支持流式 API"""
        if provider_type is None:
            return True
        streaming_providers = ["openai", "anthropic", "qwen", "kimi"]
        provider_name = (
            provider_type.value
            if hasattr(provider_type, "value")
            else str(provider_type)
        )
        return any(p in provider_name.lower() for p in streaming_providers)

    def _build_llm_request(self, topic: str, config: ScriptConfig):
        """
        构建 LLM 请求（供流式/非流式共用）

        Returns:
            (request, provider_type)
        """
        from .llm_manager import ProviderType

        provider_type = None
        if config.provider:
            try:
                provider_type = ProviderType(config.provider)
            except ValueError:
                logger.debug(f"Invalid provider '{config.provider}', using default")

        system_prompt = self.STYLE_PROMPTS.get(
            config.style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
        )
        user_prompt = self._build_prompt(topic, config)

        from .base_llm_provider import LLMRequest

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.model,
            max_tokens=config.target_words * 2,
            temperature=0.7,
        )
        return request, provider_type

    def _generate_fallback_streaming(
        self,
        topic: str,
        config: ScriptConfig,
        callback: Callable[[str], None] | None,
    ) -> GeneratedScript:
        """
        回退的流式生成（模拟流式效果）

        当 provider 不支持真正的流式时，使用此方法。
        实际上是一次性生成，但会通过回调分块返回。
        """
        if self.use_llm_manager:

            async def _run():
                result = await self._generate_async(topic, config)
                await self.llm_manager.close_all()  # type: ignore[union-attr]
                return result

            raw_content, provider_used = run_async_safely(_run)
        else:
            raw_content = self._generate_openai(topic, config)
            provider_used = "openai"

        if callback:
            chunk_size = max(1, len(raw_content) // 20)
            for i in range(0, len(raw_content), chunk_size):
                callback(raw_content[i : i + chunk_size])

        script = self._parse_response(raw_content, config)
        script.provider_used = provider_used
        return script

    def _analyze_sentiment_fast(self, text: str) -> float:
        """快速情感分析 - 基于关键词估算情感值 (-1.0 到 1.0)"""
        positive_words = [
            "好",
            "棒",
            "美",
            "喜欢",
            "爱",
            "开心",
            "高兴",
            "快乐",
            "精彩",
            "完美",
            "赞",
            "优秀",
            "成功",
            "幸福",
            "温暖",
            "感动",
            "希望",
            "期待",
            "兴奋",
            "激动",
        ]
        negative_words = [
            "坏",
            "差",
            "丑",
            "讨厌",
            "恨",
            "难过",
            "伤心",
            "痛苦",
            "糟糕",
            "失败",
            "悲剧",
            "可怜",
            "失望",
            "绝望",
            "冷漠",
            "可怕",
            "恐惧",
            "愤怒",
            "生气",
            "郁闷",
        ]
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        return (pos_count - neg_count) / total

