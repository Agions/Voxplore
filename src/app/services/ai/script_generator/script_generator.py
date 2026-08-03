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
    from app.services.ai import ScriptGenerator, ScriptConfig, ScriptStyle

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

import logging
import os
from typing import Any

from ....utils.async_bridge import run_async_safely
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

    def _build_llm_request(
        self,
        topic: str,
        config: ScriptConfig,
        *,
        multi_strategy: str | None = None,
        series_context: Any = None,
    ) -> LLMRequest:
        """构造单条脚本生成的 LLMRequest（generate_batch 内部两处共享）。

        v2.5.0 新增 ``multi_strategy`` / ``series_context`` 透传给
        :func:`build_prompt` / :func:`build_batch_prompt`，让 LLM 知道
        当前处于哪种场景 + 整季共享设定。
        """
        system_prompt = self.STYLE_PROMPTS.get(
            config.style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
        )
        return LLMRequest(
            prompt=build_prompt(
                topic,
                config,
                multi_strategy=multi_strategy,
                series_context=series_context,
            ),
            system_prompt=system_prompt,
            model=config.model,
            max_tokens=config.target_words * 2,  # 预留空间
            temperature=0.7,
        )

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
        *,
        multi_strategy: str | None = None,
        series_context: Any = None,
    ) -> GeneratedScript:
        """
        生成文案。

        v2.5.0 新增 ``multi_strategy`` / ``series_context`` 参数：
        - ``multi_strategy``: ``"single"``/``"concat"``/``"batch"``/``"series"``
        - ``series_context``: :class:`SeriesContext` 实例（仅 series 生效）

        两个参数都向后兼容：默认 ``None`` 时行为与 v2.4 完全一致。
        """
        config = config or ScriptConfig()

        if self.use_llm_manager:
            # 新架构：使用 LLMManager（异步包装为同步）
            try:

                async def _run():
                    result = await self._generate_async(
                        topic,
                        config,
                        multi_strategy=multi_strategy,
                        series_context=series_context,
                    )
                    # type: ignore[union-attr]
                    await self.llm_manager.close_all()
                    return result

                raw_content, provider_used = run_async_safely(_run)
            except Exception as e:
                logger.warning(
                    f"LLM 脚本生成失败/未配置 API Key, 使用智能范文降级: {e}"
                )
                return self._generate_single_fallback(topic, config)

        else:
            # 传统方式
            try:
                raw_content = self._generate_openai(
                    topic,
                    config,
                    multi_strategy=multi_strategy,
                    series_context=series_context,
                )
                provider_used = "openai"
            except Exception as e:
                logger.warning(f"OpenAI 脚本生成失败: {e}")
                return self._generate_single_fallback(topic, config)

        # 解析结果
        script = parse_response(raw_content, config)
        script.provider_used = provider_used

        return script

    async def _generate_async(
        self,
        topic: str,
        config: ScriptConfig,
        *,
        multi_strategy: str | None = None,
        series_context: Any = None,
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
                logger.debug(
                    f"Invalid provider '{config.provider}', using default")

        # 构建请求
        request = self._build_llm_request(
            topic,
            config,
            multi_strategy=multi_strategy,
            series_context=series_context,
        )

        # 调用 LLMManager
        # type: ignore[union-attr]
        response = await self.llm_manager.generate(request, provider=provider_type)
        provider_name = (
            response.model.split(
                "-")[0] if "-" in response.model else response.model
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

            results = run_async_safely(_run)
        else:
            results = [self.generate(topic, config)
                       for topic, config in requests]

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
            request = self._build_llm_request(topic, config)

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
                batch = short_reqs[i: i + self.batch_size]
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
            # type: ignore[union-attr]
            response = await self.llm_manager.generate(request)
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
        纯离线智能预置范文降级生成（确保无 API Key / 网络离线时 100% 不崩溃）
        """
        fallback_text = (
            f"【开场】关于《{topic}》，那些隐藏在时光深处的片段，重新浮现在眼前。\n\n"
            f"【第一幕】有些故事不需要浓墨重彩，只需要静静诉说。每一幕场景都记录着当初的心境与选择。\n\n"
            f"【第二幕】当风吹过街道，我们才发现真正触动人心的，往往是那些微小的瞬间。\n\n"
            f"【结尾】时光在向前流淌，但这些记忆永远停留在最珍贵的位置。"
        )
        return GeneratedScript(
            content=fallback_text,
            style=config.style,
            word_count=len(fallback_text),
            estimated_duration=max(10.0, config.target_words * 0.3),
            provider_used="offline_fallback",
            hook=f"关于《{topic}》，那些隐藏在时光深处的片段...",
        )

    def _generate_openai(
        self,
        topic: str,
        config: ScriptConfig,
        *,
        multi_strategy: str | None = None,
        series_context: Any = None,
    ) -> str:
        """
        传统 OpenAI 方式生成

        v2.5.0: 透传 multi_strategy / series_context 到 build_prompt。
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            system_prompt = self.STYLE_PROMPTS.get(
                config.style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
            )
            user_prompt = build_prompt(
                topic,
                config,
                multi_strategy=multi_strategy,
                series_context=series_context,
            )

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

            # type: ignore[return-value]
            return response.choices[0].message.content

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
        *,
        multi_strategy: str | None = None,
        series_context: Any = None,
    ) -> GeneratedScript:
        """生成独白文案（快捷方法）。

        v2.5.0 新增 ``multi_strategy`` / ``series_context`` 透传给
        :meth:`generate`，让 LLM 知道这是 single/concat/batch/series
        中的哪一种场景。
        """
        config = ScriptConfig(
            style=ScriptStyle.MONOLOGUE,
            tone=VoiceTone.EMOTIONAL,
            target_duration=duration,
        )

        topic = f"场景: {context}\n情感: {emotion}"
        return self.generate(
            topic,
            config,
            multi_strategy=multi_strategy,
            series_context=series_context,
        )

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
