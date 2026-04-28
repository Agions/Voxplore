#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
流式文案生成器 (Streaming Script Generator)

支持 SSE (Server-Sent Events) 和实时输出的文案生成器。
基于 ScriptGenerator 扩展，支持流式响应。

使用示例:
    from app.services.ai import StreamingScriptGenerator

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
from typing import Optional, Dict, Any, Callable, AsyncIterator

from .script_generator import ScriptGenerator
from .script_models import (
    ScriptStyle,
    VoiceTone,
    ScriptConfig,
    GeneratedScript,
)

logger = logging.getLogger(__name__)


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
        api_key: Optional[str] = None,
        use_llm_manager: bool = False,
        llm_config: Optional[Dict[str, Any]] = None,
        llm_config_file: Optional[str] = None,
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
        config: Optional[ScriptConfig] = None,
        callback: Optional[Callable[[str], None]] = None,
        sentiment_callback: Optional[Callable[[str, float], None]] = None,
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
            return self._generate_fallback_streaming(
                topic, config, callback
            )

    def _generate_streaming_llm_manager(
        self,
        topic: str,
        config: ScriptConfig,
        callback: Optional[Callable[[str], None]],
        sentiment_callback: Optional[Callable[[str, float], None]],
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
            # 尝试使用异步流式生成
            async def _run():
                return await self._generate_streaming_async(
                    topic, config, callback, sentiment_callback
                )

            # 检测是否有运行中的 event loop
            try:
                asyncio.get_running_loop()
                # 已有 loop，在新线程中运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(asyncio.run, _run()).result()
            except RuntimeError:
                # 没有运行中的 loop
                result = asyncio.run(_run())

            return result

        except Exception as e:
            logger.warning(f"流式生成失败，回退到普通方式: {e}")
            return self._generate_fallback_streaming(topic, config, callback)

    async def _generate_streaming_async(
        self,
        topic: str,
        config: ScriptConfig,
        callback: Optional[Callable[[str], None]],
        sentiment_callback: Optional[Callable[[str, float], None]],
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
        from .llm_manager import ProviderType

        # 确定提供商
        provider_type = None
        if config.provider:
            try:
                provider_type = ProviderType(config.provider)
            except ValueError:
                logger.debug(f"Invalid provider '{config.provider}', using default")

        # 构建提示词
        system_prompt = self.STYLE_PROMPTS.get(
            config.style,
            self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
        )
        user_prompt = self._build_prompt(topic, config)

        # 构建请求
        from .base_llm_provider import LLMRequest
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.model,
            max_tokens=config.target_words * 2,
            temperature=0.7,
        )

        # 检查 provider 是否支持流式
        supports_streaming = self._provider_supports_streaming(provider_type)

        if supports_streaming and self.stream_enabled:
            # 使用流式生成
            full_content = ""
            last_sentiment = 0.0

            # 使用异步迭代器获取流式响应
            async for chunk in self._stream_generate(request, provider_type):
                if chunk:
                    full_content += chunk

                    # 调用文本块回调
                    if callback:
                        callback(chunk)

                    # 尝试情感分析（如果提供回调）
                    if sentiment_callback and len(full_content) > 10:
                        sentiment = self._analyze_sentiment_fast(full_content)
                        if abs(sentiment - last_sentiment) > 0.1:  # 显著变化时回调
                            sentiment_callback(chunk, sentiment)
                            last_sentiment = sentiment

            # 关闭 provider 连接
            await self.llm_manager.close_all()

            # 解析结果
            return self._parse_response(full_content, config)
        else:
            # 不支持流式，回退到普通生成
            logger.info("Provider 不支持流式或流式已禁用，使用普通生成方式")
            response = await self.llm_manager.generate(request, provider=provider_type)
            await self.llm_manager.close_all()

            full_content = response.content

            # 仍然通过回调返回完整内容
            if callback:
                callback(full_content)

            return self._parse_response(full_content, config)

    async def _stream_generate(
        self,
        request,
        provider_type: Optional[Any],
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
            # 调用 LLMManager 的流式方法（如果支持）
            if hasattr(self.llm_manager, 'generate_streaming'):
                async for chunk in self.llm_manager.generate_streaming(request, provider=provider_type):
                    yield chunk
            else:
                # 回退: 普通生成
                response = await self.llm_manager.generate(request, provider=provider_type)
                yield response.content

        except Exception as e:
            logger.error(f"流式生成错误: {e}")
            yield ""

    def _provider_supports_streaming(self, provider_type: Optional[Any]) -> bool:
        """
        检查 provider 是否支持流式 API

        Args:
            provider_type: ProviderType 枚举值

        Returns:
            是否支持流式
        """
        # OpenAI 兼容的 providers 通常都支持流式
        # 这里可以根据实际情况扩展
        if provider_type is None:
            return True  # 默认假设支持

        # 已知支持流式的 providers
        streaming_providers = [
            'openai',
            'anthropic',
            'qwen',
            'kimi',
        ]

        provider_name = provider_type.value if hasattr(provider_type, 'value') else str(provider_type)

        return any(p in provider_name.lower() for p in streaming_providers)

    def _generate_fallback_streaming(
        self,
        topic: str,
        config: ScriptConfig,
        callback: Optional[Callable[[str], None]],
    ) -> GeneratedScript:
        """
        回退的流式生成（模拟流式效果）

        当 provider 不支持真正的流式时，使用此方法。
        实际上是一次性生成，但会通过回调分块返回。

        Args:
            topic: 主题
            config: 生成配置
            callback: 文本块回调

        Returns:
            完整的 GeneratedScript
        """
        # 使用普通生成
        if self.use_llm_manager:
            # 复用父类的新架构
            async def _run():
                result = await self._generate_async(topic, config)
                await self.llm_manager.close_all()
                return result

            try:
                asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    raw_content, provider_used = pool.submit(asyncio.run, _run()).result()
            except RuntimeError:
                raw_content, provider_used = asyncio.run(_run())
        else:
            raw_content = self._generate_openai(topic, config)
            provider_used = "openai"

        # 通过回调分块返回（模拟流式）
        if callback:
            # 分块大小
            chunk_size = max(1, len(raw_content) // 20)

            for i in range(0, len(raw_content), chunk_size):
                chunk = raw_content[i:i + chunk_size]
                callback(chunk)

        # 解析结果
        script = self._parse_response(raw_content, config)
        script.provider_used = provider_used

        return script

    def generate_streaming_async(
        self,
        topic: str,
        config: Optional[ScriptConfig] = None,
        callback: Optional[Callable[[str], None]] = None,
        sentiment_callback: Optional[Callable[[str, float], None]] = None,
    ) -> asyncio.Future:
        """
        异步流式生成（返回 Future）

        便利方法，返回 asyncio.Future 对象。

        Args:
            topic: 主题
            config: 生成配置
            callback: 文本块回调
            sentiment_callback: 情感分析回调

        Returns:
            asyncio.Future[GeneratedScript]
        """
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            None,
            self.generate_streaming,
            topic, config, callback, sentiment_callback
        )

    def generate_monologue_streaming(
        self,
        context: str,
        emotion: str = "neutral",
        duration: float = 30.0,
        callback: Optional[Callable[[str], None]] = None,
    ) -> GeneratedScript:
        """
        流式生成独白文案

        快捷方法，生成第一人称情感化独白。

        Args:
            context: 场景/情境描述
            emotion: 情感（如：惆怅、欣喜、思念）
            duration: 目标时长（秒）
            callback: 文本块回调

        Returns:
            生成的文案对象
        """
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
        callback: Optional[Callable[[str], None]] = None,
    ) -> GeneratedScript:
        """
        流式生成解说文案

        快捷方法，生成客观信息密集的解说风格文案。

        Args:
            topic: 解说主题
            duration: 目标时长（秒）
            tone: 语气
            callback: 文本块回调

        Returns:
            生成的文案对象
        """
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
        config: Optional[ScriptConfig] = None,
    ) -> AsyncIterator[str]:
        """
        生成 SSE (Server-Sent Events) 格式的流

        每次 Yields 一个 SSE 格式的事件行。

        Args:
            topic: 主题
            config: 生成配置

        Yields:
            SSE 格式的字符串行
        """
        async def _sse_generator():
            cfg = config if config is not None else ScriptConfig()

            full_content = ""

            async for chunk in self._stream_sse_content(topic, cfg):
                if chunk:
                    full_content += chunk
                    # SSE 格式: data: {chunk}\n\n
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'content': full_content})}\n\n"

        return _sse_generator()

    async def _stream_sse_content(
        self,
        topic: str,
        config: ScriptConfig,
    ) -> AsyncIterator[str]:
        """
        内部方法: 生成 SSE 格式内容流

        Args:
            topic: 主题
            config: 生成配置

        Yields:
            文本块
        """
        try:
            # 检查是否支持流式
            supports_streaming = True  # 简化处理

            if supports_streaming and self.use_llm_manager and self.llm_manager:
                from .llm_manager import ProviderType

                provider_type = None
                if config.provider:
                    try:
                        provider_type = ProviderType(config.provider)
                    except ValueError:
                        logger.warning(f"Invalid provider type: {config.provider!r}, falling back to None")

                system_prompt = self.STYLE_PROMPTS.get(
                    config.style,
                    self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
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

                if hasattr(self.llm_manager, 'generate_streaming'):
                    async for chunk in self.llm_manager.generate_streaming(request, provider=provider_type):
                        if chunk:
                            yield chunk
                else:
                    response = await self.llm_manager.generate(request, provider=provider_type)
                    yield response.content
            else:
                # 回退到普通生成
                response = await self._generate_async(topic, config)
                yield response[0] if isinstance(response, tuple) else response

        except Exception as e:
            logger.error(f"SSE 流生成错误: {e}")
            yield ""

    def _analyze_sentiment_fast(self, text: str) -> float:
        """
        快速情感分析

        基于关键词的简单情感估算。
        返回 -1.0 (负面) 到 1.0 (正面) 的情感值。

        Args:
            text: 待分析的文本

        Returns:
            情感值 (-1.0 到 1.0)
        """
        # 简化的情感词典
        positive_words = [
            '好', '棒', '美', '喜欢', '爱', '开心', '高兴', '快乐',
            '精彩', '完美', '赞', '优秀', '成功', '幸福', '温暖',
            '感动', '希望', '期待', '兴奋', '激动',
        ]

        negative_words = [
            '坏', '差', '丑', '讨厌', '恨', '难过', '伤心', '痛苦',
            '糟糕', '失败', '悲剧', '可怜', '失望', '绝望', '冷漠',
            '可怕', '恐惧', '愤怒', '生气', '郁闷',
        ]

        # 简单计数
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)

        total = pos_count + neg_count
        if total == 0:
            return 0.0  # 中性

        # 返回情感倾向 (-1 到 1)
        return (pos_count - neg_count) / total

    def stream_to_iterator(
        self,
        topic: str,
        config: Optional[ScriptConfig] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        生成流式输出的异步迭代器

        每个迭代项是一个包含类型和内容的字典:
        - {'type': 'chunk', 'content': '文本块'}
        - {'type': 'sentiment', 'value': 0.5, 'text': '当前文本'}
        - {'type': 'done', 'content': '完整内容'}

        Args:
            topic: 主题
            config: 生成配置

        Yields:
            事件字典
        """
        async def _iter():
            cfg = config if config is not None else ScriptConfig()
            last_sentiment = 0.0
            full_content = ""

            async for chunk in self._stream_content(topic, cfg):
                if chunk:
                    full_content += chunk
                    yield {'type': 'chunk', 'content': chunk}

                    # 每隔一段时间检测情感变化
                    if len(full_content) % 50 < 10:
                        sentiment = self._analyze_sentiment_fast(full_content)
                        if abs(sentiment - last_sentiment) > 0.15:
                            yield {'type': 'sentiment', 'value': sentiment, 'text': full_content[-20:]}
                            last_sentiment = sentiment

            yield {'type': 'done', 'content': full_content}

        return _iter()

    async def _stream_content(
        self,
        topic: str,
        config: ScriptConfig,
    ) -> AsyncIterator[str]:
        """
        内部方法: 生成内容流

        Args:
            topic: 主题
            config: 生成配置

        Yields:
            文本块
        """
        try:
            # 直接复用 _stream_sse_content
            async for chunk in self._stream_sse_content(topic, config):
                yield chunk
        except Exception as e:
            logger.error(f"内容流错误: {e}")
            yield ""


# =========== 便捷函数 ===========

def generate_script_streaming(
    topic: str,
    config: Optional[ScriptConfig] = None,
    callback: Optional[Callable[[str], None]] = None,
) -> GeneratedScript:
    """
    流式生成文案的便捷函数

    Args:
        topic: 主题
        config: 生成配置
        callback: 文本块回调

    Returns:
        生成的文案
    """
    generator = StreamingScriptGenerator(use_llm_manager=True)
    return generator.generate_streaming(topic, config, callback)


if __name__ == '__main__':
    # 演示用法
    print("StreamingScriptGenerator 演示")
    print("-" * 50)

    # 简单的回调函数
    def on_chunk(chunk: str):
        print(chunk, end='', flush=True)

    def on_sentiment(text: str, sentiment: float):
        print(f"\n[sentiment changed: {sentiment:.2f}]", end='')

    # 演示（需要配置 LLM）
    try:
        generator = StreamingScriptGenerator(use_llm_manager=True)

        script = generator.generate_streaming(
            topic="这部电影讲述了一个感人的故事",
            config=ScriptConfig(
                style=ScriptStyle.MONOLOGUE,
                target_duration=30,
            ),
            callback=on_chunk,
            sentiment_callback=on_sentiment,
        )

        print("\n\n" + "=" * 50)
        print("生成完成!")
        print(f"字数: {script.word_count}")
        print(f"预计时长: {script.estimated_duration:.1f}s")

    except Exception as e:
        print(f"\n演示需要配置 LLM: {e}")
