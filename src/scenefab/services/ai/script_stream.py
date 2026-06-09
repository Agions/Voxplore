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
import json
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from .script_generator import ScriptGenerator
from .script_models import (
    GeneratedScript,
    ScriptConfig,
    ScriptStyle,
    VoiceTone,
)

logger = logging.getLogger(__name__)

__all__ = ["StreamingScriptGenerator", "generate_script_streaming"]


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

            try:
                asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(asyncio.run, _run()).result()
            except RuntimeError:
                result = asyncio.run(_run())

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

            async for chunk in self._stream_generate(request, provider_type):
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

    async def _stream_generate(
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
            if hasattr(self.llm_manager, "generate_streaming"):
                async for chunk in self.llm_manager.generate_streaming(  # type: ignore[union-attr]
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

            try:
                asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    raw_content, provider_used = pool.submit(
                        asyncio.run, _run()
                    ).result()
            except RuntimeError:
                raw_content, provider_used = asyncio.run(_run())
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

    def generate_streaming_async(
        self,
        topic: str,
        config: ScriptConfig | None = None,
        callback: Callable[[str], None] | None = None,
        sentiment_callback: Callable[[str, float], None] | None = None,
    ) -> asyncio.Future:
        """异步流式生成（返回 Future）"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            None, self.generate_streaming, topic, config, callback, sentiment_callback
        )

    def generate_monologue_streaming(
        self,
        context: str,
        emotion: str = "neutral",
        duration: float = 30.0,
        callback: Callable[[str], None] | None = None,
    ) -> GeneratedScript:
        """流式生成独白文案"""
        config = ScriptConfig(
            style=ScriptStyle.MONOLOGUE,
            tone=VoiceTone.EMOTIONAL,
            target_duration=duration,
        )
        topic = f"场景: {context}\n情感: {emotion}"
        return self.generate_streaming(topic, config, callback=callback)

    def generate_commentary_streaming(
        self,
        topic: str,
        duration: float = 60.0,
        tone: VoiceTone = VoiceTone.NEUTRAL,
        callback: Callable[[str], None] | None = None,
    ) -> GeneratedScript:
        """流式生成解说文案"""
        config = ScriptConfig(
            style=ScriptStyle.COMMENTARY,
            tone=tone,
            target_duration=duration,
            include_hook=True,
        )
        return self.generate_streaming(topic, config, callback=callback)

    def generate_sse_stream(
        self,
        topic: str,
        config: ScriptConfig | None = None,
    ) -> AsyncIterator[str]:
        """生成 SSE (Server-Sent Events) 格式的流"""
        cfg = config if config is not None else ScriptConfig()

        async def _sse_generator():
            full_content = ""
            async for chunk in self._stream_sse_content(topic, cfg):
                if chunk:
                    full_content += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': full_content})}\n\n"

        return _sse_generator()  # type: ignore[no-any-return]

    async def _stream_sse_content(
        self,
        topic: str,
        config: ScriptConfig,
    ) -> AsyncIterator[str]:
        """内部方法: 生成 SSE 格式内容流"""
        try:
            if self.use_llm_manager and self.llm_manager:
                request, provider_type = self._build_llm_request(topic, config)
                if hasattr(self.llm_manager, "generate_streaming"):
                    async for chunk in self.llm_manager.generate_streaming(
                        request, provider=provider_type
                    ):
                        if chunk:
                            yield chunk
                else:
                    response = await self.llm_manager.generate(
                        request, provider=provider_type
                    )
                    yield response.content
            else:
                response = await self._generate_async(topic, config)  # type: ignore[assignment]
                yield response[0] if isinstance(response, tuple) else response
        except Exception as e:
            logger.error(f"SSE 流生成错误: {e}")
            yield ""

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

    def stream_to_iterator(
        self,
        topic: str,
        config: ScriptConfig | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """生成流式输出的异步迭代器"""
        cfg = config if config is not None else ScriptConfig()

        async def _iter():
            last_sentiment = 0.0
            full_content = ""
            # 直接调用 _stream_sse_content（内联 _stream_content 逻辑）
            async for chunk in self._stream_sse_content(topic, cfg):
                if chunk:
                    full_content += chunk
                    yield {"type": "chunk", "content": chunk}
                    if len(full_content) % 50 < 10:
                        sentiment = self._analyze_sentiment_fast(full_content)
                        if abs(sentiment - last_sentiment) > 0.15:
                            yield {
                                "type": "sentiment",
                                "value": sentiment,
                                "text": full_content[-20:],
                            }
                            last_sentiment = sentiment
            yield {"type": "done", "content": full_content}

        return _iter()  # type: ignore[no-any-return]


# =========== 便捷函数 ===========


def generate_script_streaming(
    topic: str,
    config: ScriptConfig | None = None,
    callback: Callable[[str], None] | None = None,
) -> GeneratedScript:
    """流式生成文案的便捷函数"""
    generator = StreamingScriptGenerator(use_llm_manager=True)
    return generator.generate_streaming(topic, config, callback)
