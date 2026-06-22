"""
AI 文案生成器 (Script Generator)

使用 LLM 生成视频解说文案、独白台词等内容。

支持多种风格:
- 解说风格: 客观、信息密集
- 独白风格: 第一人称、情感化
- 混剪文案: 节奏感、关键词

支持多 LLM 提供商:
- 通义千问 Qwen 3
- Kimi k2
- 智谱 GLM-5
- OpenAI (兼容)

使用示例:
    from scenefab.services.ai import ScriptGenerator, ScriptConfig, ScriptStyle

    # 使用新架构 (LLMManager)
    generator = ScriptGenerator(use_llm_manager=True)

    script = generator.generate(
        topic="这部电影讲述了一个感人的故事",
        style=ScriptStyle.COMMENTARY,
        duration=60,
    )
    print(script.content)

    # 使用传统方式 (OpenAI)
    generator = ScriptGenerator(api_key="your-api-key")
"""

import asyncio
import logging
import os
from typing import Any

from ..base_llm_provider import LLMRequest
from ..llm_manager import LLMManager, load_llm_config
from ..model_catalog import DEFAULT_MODELS
from ..script_models import (
    GeneratedScript,
    ScriptConfig,
    ScriptStyle,
    VoiceTone,
)
from ._prompt_builder import build_batch_prompt, build_prompt
from ._response_parser import (
    parse_batch_response,
    parse_response,
    split_to_captions,
)
from ._style_prompts import STYLE_PROMPTS

logger = logging.getLogger(__name__)

__all__ = ["ScriptGenerator", "generate_script"]


class ScriptGenerator:
    """
    AI 文案生成器

    支持多 LLM 后端（通义千问、Kimi、GLM-5、OpenAI），生成不同风格的视频文案

    使用示例:
        # 使用新架构 (LLMManager) - 推荐
        generator = ScriptGenerator(use_llm_manager=True)

        # 生成解说文案
        script = generator.generate_commentary(
            topic="分析《流浪地球》的科学设定",
            duration=60,
        )

        # 使用传统方式 (OpenAI) - 兼容
        generator = ScriptGenerator(api_key="sk-xxx")
    """

    # 风格对应的系统提示词（引用模块级常量）
    STYLE_PROMPTS = STYLE_PROMPTS

    def __init__(
        self,
        api_key: str | None = None,
        use_llm_manager: bool = False,
        llm_config: dict[str, Any] | None = None,
        llm_config_file: str | None = None,
        batch_size: int = 4,  # 批量生成的段数
        min_words_for_batch: int = 50,  # 小于此字数的短请求优先合并
    ):
        """
        初始化文案生成器

        Args:
            api_key: OpenAI API Key（传统方式）
            use_llm_manager: 是否使用 LLMManager（新架构）
            llm_config: LLM 配置字典
            llm_config_file: LLM 配置文件路径
            batch_size: 批量生成的最大段数
            min_words_for_batch: 小于此字数的请求会被合并
        """
        self.use_llm_manager = use_llm_manager
        self.llm_manager: LLMManager | None = None
        self.batch_size = batch_size
        self.min_words_for_batch = min_words_for_batch

        if use_llm_manager:
            # 使用新架构
            if llm_config:
                load = llm_config
            elif llm_config_file:
                load = load_llm_config(llm_config_file)
            else:
                load = load_llm_config()

            self.llm_manager = LLMManager(load)
            logger.info("LLMManager 初始化成功")
            logger.info(
                "默认提供商: "
                f"{load.get('LLM', {}).get('default_provider', 'deepseek')}, "
                f"主力模型: {DEFAULT_MODELS['deepseek']}"
            )
            logger.info(
                f"可用提供商: {[p.value for p in self.llm_manager.get_available_providers()]}"
            )

        elif api_key:
            # 使用直连 OpenAI 方式
            # 创建一个简单的包装类
            self.api_key = api_key
            logger.info("使用传统 OpenAI 方式")

        else:
            # 尝试从环境变量获取
            env_key = os.getenv("OPENAI_API_KEY")
            if env_key:
                self.api_key = env_key
                logger.info("使用环境变量 OPENAI_API_KEY")
            else:
                raise ValueError("请提供 api_key 或设置 use_llm_manager=True")

    def generate(
        self,
        topic: str,
        config: ScriptConfig | None = None,
    ) -> GeneratedScript:
        """
        生成文案

        Args:
            topic: 主题/内容描述
            config: 生成配置

        Returns:
            生成的文案对象
        """
        config = config or ScriptConfig()

        if self.use_llm_manager:
            # 新架构：使用 LLMManager（异步包装为同步）
            # 避免在已有 event loop 的线程中调用 run_until_complete
            async def _run():
                result = await self._generate_async(topic, config)
                await self.llm_manager.close_all()  # type: ignore[union-attr]
                return result

            try:
                asyncio.get_running_loop()
                # 已有 loop，在新线程中运行
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    raw_content, provider_used = pool.submit(
                        asyncio.run, _run()
                    ).result()
            except RuntimeError:
                # 没有运行中的 loop
                raw_content, provider_used = asyncio.run(_run())

        else:
            # 传统方式
            raw_content = self._generate_openai(topic, config)
            provider_used = "openai"

        # 解析结果
        script = parse_response(raw_content, config)
        script.provider_used = provider_used

        return script

    async def _generate_async(
        self,
        topic: str,
        config: ScriptConfig,
    ) -> tuple[str, str]:
        """
        异步生成（使用 LLMManager）

        Returns:
            (content, provider_name)
        """
        # 确定提供商
        provider_type = None
        if config.provider:
            try:
                from ..llm_manager import ProviderType

                provider_type = ProviderType(config.provider)
            except ValueError:
                logger.debug(f"Invalid provider '{config.provider}', using default")

        # 构建请求
        system_prompt = self.STYLE_PROMPTS.get(
            config.style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
        )
        user_prompt = build_prompt(topic, config)

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.model,
            max_tokens=config.target_words * 2,  # 预留空间
            temperature=0.7,
        )

        # 调用 LLMManager
        response = await self.llm_manager.generate(request, provider=provider_type)  # type: ignore[union-attr]
        provider_name = (
            response.model.split("-")[0] if "-" in response.model else response.model
        )

        return response.content, provider_name

    def generate_batch(
        self,
        requests: list[tuple[str, ScriptConfig]],
    ) -> list[GeneratedScript]:
        """
        批量生成多段文案（合并 API 调用）

        Args:
            requests: [(topic, config), ...] 请求列表

        Returns:
            生成的文案列表
        """
        if not requests:
            return []

        if self.use_llm_manager:

            async def _run():
                results = await self._generate_batch_async(requests)
                await self.llm_manager.close_all()  # type: ignore[union-attr]
                return results

            try:
                asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    results = pool.submit(asyncio.run, _run()).result()
            except RuntimeError:
                results = asyncio.run(_run())
        else:
            results = [self.generate(topic, config) for topic, config in requests]

        return results  # type: ignore[no-any-return]

    async def _generate_batch_async(
        self,
        requests: list[tuple[str, ScriptConfig]],
    ) -> list[GeneratedScript]:
        """
        异步批量生成（使用 LLMManager）

        策略:
        1. 短请求（字数 < min_words_for_batch）优先合并
        2. 合并后每批最多 batch_size 个请求
        3. 长请求单独调用
        """
        if not self.llm_manager:
            raise ValueError("LLMManager 未初始化")

        # 分类：短请求 vs 长请求
        short_reqs = []  # 需要合并的短请求
        long_reqs = []  # 单独处理的长请求

        for topic, config in requests:
            if config.target_words < self.min_words_for_batch:
                short_reqs.append((topic, config))
            else:
                long_reqs.append((topic, config))

        results: list[GeneratedScript] = []

        # 处理长请求（单独调用）
        for topic, config in long_reqs:
            system_prompt = self.STYLE_PROMPTS.get(
                config.style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
            )
            user_prompt = build_prompt(topic, config)

            request = LLMRequest(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=config.model,
                max_tokens=config.target_words * 2,
                temperature=0.7,
            )

            try:
                response = await self.llm_manager.generate(request)
                script = parse_response(response.content, config)
                script.provider_used = (
                    response.model.split("-")[0]
                    if "-" in response.model
                    else response.model
                )
                results.append(script)
            except Exception as e:
                logger.warning(f"长请求生成失败: {e}")
                script = self._generate_single_fallback(topic, config)
                results.append(script)

        # 处理短请求（批量合并调用）
        if short_reqs:
            # 分批：每批最多 batch_size 个
            for i in range(0, len(short_reqs), self.batch_size):
                batch = short_reqs[i : i + self.batch_size]
                if len(batch) == 1:
                    topic, config = batch[0]
                    script = self._generate_single_fallback(topic, config)
                    results.append(script)
                else:
                    batch_result = await self._generate_batch_single_call(batch)
                    results.extend(batch_result)

        return results

    async def _generate_batch_single_call(
        self,
        batch: list[tuple[str, ScriptConfig]],
    ) -> list[GeneratedScript]:
        """
        单次 API 调用生成多个短请求
        """
        if not batch:
            return []

        if len(batch) == 1:
            topic, config = batch[0]
            return [self._generate_single_fallback(topic, config)]

        # 使用第一个请求的风格作为基础
        first_topic, first_config = batch[0]
        style = first_config.style

        system_prompt = self.STYLE_PROMPTS.get(
            style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
        )

        # 构建批量请求的提示词
        user_prompt = build_batch_prompt(batch)

        # 计算总字数需求
        total_words = sum(config.target_words for _, config in batch)
        max_tokens = int(total_words * 2 * 1.2)

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=first_config.model,
            max_tokens=max_tokens,
            temperature=0.7,
        )

        try:
            response = await self.llm_manager.generate(request)  # type: ignore[union-attr]
            return parse_batch_response(response.content, batch)
        except Exception as e:
            logger.warning(f"批量生成失败，回退到逐段调用: {e}")
            return [
                self._generate_single_fallback(topic, config) for topic, config in batch
            ]

    def _generate_single_fallback(
        self,
        topic: str,
        config: ScriptConfig,
    ) -> GeneratedScript:
        """
        单独生成单个文案（回退方法）
        """
        if self.use_llm_manager and self.llm_manager:

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

            script = parse_response(raw_content, config)
            script.provider_used = provider_used
            return script
        else:
            raw_content = self._generate_openai(topic, config)
            return parse_response(raw_content, config)

    def _generate_openai(
        self,
        topic: str,
        config: ScriptConfig,
    ) -> str:
        """
        传统 OpenAI 方式生成
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            system_prompt = self.STYLE_PROMPTS.get(
                config.style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
            )
            user_prompt = build_prompt(topic, config)

            response = client.chat.completions.create(
                model=config.model or "gpt-5",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=config.temperature
                if hasattr(config, "temperature")
                else 0.7,
                max_tokens=2000,
            )

            return response.choices[0].message.content  # type: ignore[return-value]

        except ImportError:
            raise ImportError("请安装 openai: pip install openai")
        except Exception as e:
            raise RuntimeError(f"OpenAI API 调用失败: {e}")

    def generate_commentary(
        self,
        topic: str,
        duration: float = 60.0,
        tone: VoiceTone = VoiceTone.NEUTRAL,
    ) -> GeneratedScript:
        """生成解说文案（快捷方法）"""
        config = ScriptConfig(
            style=ScriptStyle.COMMENTARY,
            tone=tone,
            target_duration=duration,
            include_hook=True,
        )
        return self.generate(topic, config)

    def generate_monologue(
        self,
        context: str,
        emotion: str = "neutral",
        duration: float = 30.0,
    ) -> GeneratedScript:
        """生成独白文案（快捷方法）"""
        config = ScriptConfig(
            style=ScriptStyle.MONOLOGUE,
            tone=VoiceTone.EMOTIONAL,
            target_duration=duration,
        )

        topic = f"场景: {context}\n情感: {emotion}"
        return self.generate(topic, config)

    def generate_viral(
        self,
        topic: str,
        duration: float = 30.0,
        keywords: list[str] | None = None,
    ) -> GeneratedScript:
        """生成爆款文案（快捷方法）"""
        config = ScriptConfig(
            style=ScriptStyle.VIRAL,
            tone=VoiceTone.EXCITED,
            target_duration=duration,
            include_hook=True,
            keywords=keywords or [],
        )
        return self.generate(topic, config)

    # 委托给独立模块的方法（保持原有 API 兼容）
    def _build_prompt(self, topic: str, config: ScriptConfig) -> str:
        return build_prompt(topic, config)

    def _build_batch_prompt(self, batch: list[tuple[str, ScriptConfig]]) -> str:
        return build_batch_prompt(batch)

    def _parse_response(self, content: str, config: ScriptConfig) -> GeneratedScript:
        return parse_response(content, config)

    def _parse_batch_response(
        self, content: str, batch: list[tuple[str, ScriptConfig]]
    ) -> list[GeneratedScript]:
        return parse_batch_response(content, batch)

    def _extract_segment(
        self, content: str, segment_num: int, config: ScriptConfig
    ) -> str:
        from ._response_parser import extract_segment

        return extract_segment(content, segment_num, config)

    def split_to_captions(
        self, script: GeneratedScript, _max_chars: int = 20
    ) -> list[dict[str, Any]]:
        return split_to_captions(script, _max_chars)


# =========== 便捷函数 ===========


def generate_script(
    topic: str,
    style: ScriptStyle = ScriptStyle.COMMENTARY,
    duration: float = 60.0,
    use_llm_manager: bool = True,
    api_key: str | None = None,
) -> GeneratedScript:
    """
    快速生成文案

    Args:
        topic: 主题
        style: 风格
        duration: 时长
        use_llm_manager: 是否使用 LLMManager
        api_key: API Key (传统方式)
    """
    generator = ScriptGenerator(
        api_key=api_key,
        use_llm_manager=use_llm_manager,
    )
    config = ScriptConfig(style=style, target_duration=duration)
    return generator.generate(topic, config)
