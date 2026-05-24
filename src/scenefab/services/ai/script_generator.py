#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


import os
import asyncio
from typing import Optional, List, Dict, Any

from .base_llm_provider import LLMRequest
from .llm_manager import LLMManager, load_llm_config
from .script_models import (
    ScriptStyle,
    VoiceTone,
    ScriptConfig,
    ScriptSegment,
    GeneratedScript,
)
import logging
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

    # 风格对应的系统提示词
    STYLE_PROMPTS = {
        ScriptStyle.COMMENTARY: """你是一位专业的视频解说文案撰写者。
你的文案特点是：
- 客观、信息密集
- 节奏紧凑，每句话都有料
- 适合配合画面解说
- 开头要有钩子，能在3秒内抓住观众
- 避免过于口语化，但要自然流畅""",

        ScriptStyle.MONOLOGUE: """你是一位擅长写第一人称独白的文案作者。
你的文案特点是：
- 第一人称视角，情感真挚
- 像在对观众倾诉心声
- 有画面感，能引发共鸣
- 适合配合沉浸式视频
- 用词优美但不矫情""",

        ScriptStyle.VIRAL: """你是一位爆款短视频文案高手。
你的文案特点是：
- 开头必须在3秒内抓住眼球
- 节奏极快，信息密度高
- 使用悬念、反转、情绪词
- 适合15-60秒的短视频
- 每一句都要有看点""",

        ScriptStyle.NARRATION: """你是一位故事性旁白撰写者。
你的文案特点是：
- 讲故事的方式娓娓道来
- 有起承转合的结构
- 引导观众情绪
- 适合纪录片、Vlog风格
- 温暖而有深度""",

        ScriptStyle.EDUCATIONAL: """你是一位教育类视频文案专家。
你的文案特点是：
- 逻辑清晰、层次分明
- 复杂概念简单化
- 适合知识类视频
- 节奏适中，便于理解
- 有总结和重点强调""",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_llm_manager: bool = False,
        llm_config: Optional[Dict[str, Any]] = None,
        llm_config_file: Optional[str] = None,
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
        self.llm_manager: Optional[LLMManager] = None
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
            logger.info(f"默认提供商: {load.get('LLM', {}).get('default_provider', 'qwen')}")
            logger.info(f"可用提供商: {[p.value for p in self.llm_manager.get_available_providers()]}")

        elif api_key:
            # 使用传统方式 (兼容)
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
        config: Optional[ScriptConfig] = None,
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
                await self.llm_manager.close_all()
                return result

            try:
                asyncio.get_running_loop()
                # 已有 loop，在新线程中运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    raw_content, provider_used = pool.submit(asyncio.run, _run()).result()
            except RuntimeError:
                # 没有运行中的 loop
                raw_content, provider_used = asyncio.run(_run())

        else:
            # 传统方式
            raw_content = self._generate_openai(topic, config)
            provider_used = "openai"

        # 解析结果
        script = self._parse_response(raw_content, config)
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
                from .llm_manager import ProviderType
                provider_type = ProviderType(config.provider)
            except ValueError:
                logger.debug(f"Invalid provider '{config.provider}', using default")

        # 构建请求
        system_prompt = self.STYLE_PROMPTS.get(
            config.style,
            self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
        )
        user_prompt = self._build_prompt(topic, config)

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.model,
            max_tokens=config.target_words * 2,  # 预留空间
            temperature=0.7,
        )

        # 调用 LLMManager
        response = await self.llm_manager.generate(request, provider=provider_type)
        provider_name = response.model.split("-")[0] if "-" in response.model else response.model

        return response.content, provider_name

    def generate_batch(
        self,
        requests: List[tuple[str, ScriptConfig]],
    ) -> List[GeneratedScript]:
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
                await self.llm_manager.close_all()
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

        return results

    async def _generate_batch_async(
        self,
        requests: List[tuple[str, ScriptConfig]],
    ) -> List[GeneratedScript]:
        """
        异步批量生成（使用 LLMManager）

        策略:
        1. 短请求（字数 < min_words_for_batch）优先合并
        2. 合并后每批最多 batch_size 个请求
        3. 长请求单独调用

        Args:
            requests: [(topic, config), ...]

        Returns:
            生成的文案列表
        """
        if not self.llm_manager:
            raise ValueError("LLMManager 未初始化")

        # 分类：短请求 vs 长请求
        short_reqs = []  # 需要合并的短请求
        long_reqs = []   # 单独处理的长请求

        for topic, config in requests:
            if config.target_words < self.min_words_for_batch:
                short_reqs.append((topic, config))
            else:
                long_reqs.append((topic, config))

        results: List[GeneratedScript] = []

        # 处理长请求（单独调用）
        for topic, config in long_reqs:
            system_prompt = self.STYLE_PROMPTS.get(
                config.style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
            )
            user_prompt = self._build_prompt(topic, config)

            request = LLMRequest(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=config.model,
                max_tokens=config.target_words * 2,
                temperature=0.7,
            )

            try:
                response = await self.llm_manager.generate(request)
                script = self._parse_response(response.content, config)
                script.provider_used = response.model.split("-")[0] if "-" in response.model else response.model
                results.append(script)
            except Exception as e:
                logger.warning(f"长请求生成失败: {e}")
                script = self._generate_single_fallback(topic, config)
                results.append(script)

        # 处理短请求（批量合并调用）
        if short_reqs:
            # 分批：每批最多 batch_size 个
            for i in range(0, len(short_reqs), self.batch_size):
                batch = short_reqs[i:i + self.batch_size]
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
        batch: List[tuple[str, ScriptConfig]],
    ) -> List[GeneratedScript]:
        """
        单次 API 调用生成多个短请求

        Args:
            batch: [(topic, config), ...] 同风格的短请求

        Returns:
            生成的文案列表
        """
        if not batch:
            return []

        if len(batch) == 1:
            topic, config = batch[0]
            return [self._generate_single_fallback(topic, config)]

        # 使用第一个请求的风格作为基础
        first_topic, first_config = batch[0]
        style = first_config.style

        system_prompt = self.STYLE_PROMPTS.get(style, self.STYLE_PROMPTS[ScriptStyle.COMMENTARY])

        # 构建批量请求的提示词
        user_prompt = self._build_batch_prompt(batch)

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
            response = await self.llm_manager.generate(request)
            return self._parse_batch_response(response.content, batch)
        except Exception as e:
            logger.warning(f"批量生成失败，回退到逐段调用: {e}")
            return [self._generate_single_fallback(topic, config) for topic, config in batch]

    def _build_batch_prompt(self, batch: List[tuple[str, ScriptConfig]]) -> str:
        """
        构建批量请求的提示词
        """
        if not batch:
            return ""

        parts = ["请为以下多个主题分别生成视频文案。\n"]

        for i, (topic, config) in enumerate(batch, 1):
            parts.append(f"\n=== 段落 {i} ===")
            parts.append(f"主题: {topic}")
            parts.append(f"字数要求: 约 {config.target_words} 字")

            tone_map = {
                VoiceTone.NEUTRAL: "中性、客观",
                VoiceTone.EXCITED: "兴奋、激动",
                VoiceTone.CALM: "平静、舒缓",
                VoiceTone.MYSTERIOUS: "神秘、悬疑",
                VoiceTone.EMOTIONAL: "情感、深情",
                VoiceTone.HUMOROUS: "幽默、轻松",
            }
            parts.append(f"语气风格: {tone_map.get(config.tone, '中性')}")

            if config.include_hook:
                parts.append("要求: 开头3秒必须有吸引力的「钩子」")

            if config.keywords:
                parts.append(f"必须包含关键词: {', '.join(config.keywords)}")

            parts.append("")

        parts.append("""
输出格式要求：
1. 用空行分隔各段落
2. 每个段落前标注【段落N】
3. 每个段落独立成篇，有完整的开头和结尾
4. 不要在段落之间添加标题或解释
""")

        return "\n".join(parts)

    def _parse_batch_response(
        self,
        content: str,
        batch: List[tuple[str, ScriptConfig]],
    ) -> List[GeneratedScript]:
        """
        解析批量生成的响应
        """
        content = content.strip()

        scripts = []
        for i, (topic, config) in enumerate(batch):
            segment = self._extract_segment(content, i + 1, config)
            if segment:
                script = self._parse_response(segment, config)
            else:
                script = self._parse_response(content if i == 0 else "", config)
            scripts.append(script)

        return scripts

    def _extract_segment(
        self,
        content: str,
        segment_num: int,
        config: ScriptConfig,
    ) -> str:
        """
        从批量响应中提取指定段落
        """
        import re

        # 尝试查找【段落N】标记
        pattern = rf"【段落{segment_num}】\s*(.*?)(?=【段落\d+】|$)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            text = match.group(1).strip()
            text = re.sub(r"^【段落\d+】\s*", "", text, flags=re.MULTILINE)
            return text

        # 回退：按段落数量平均分割
        positions = []
        for m in re.finditer(r"【段落\d+】", content):
            positions.append(m.start())

        if len(positions) > segment_num:
            start = positions[segment_num - 1]
            end = positions[segment_num] if segment_num < len(positions) else len(content)
            text = content[start:end]
            text = re.sub(r"^【段落\d+】\s*", "", text, flags=re.MULTILINE)
            return text.strip()

        return ""

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
                await self.llm_manager.close_all()
                return result

            try:
                asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    raw_content, provider_used = pool.submit(asyncio.run, _run()).result()
            except RuntimeError:
                raw_content, provider_used = asyncio.run(_run())

            script = self._parse_response(raw_content, config)
            script.provider_used = provider_used
            return script
        else:
            raw_content = self._generate_openai(topic, config)
            return self._parse_response(raw_content, config)

    def _generate_openai(
        self,
        topic: str,
        config: ScriptConfig,
    ) -> str:
        """
        传统 OpenAI 方式生成

        Returns:
            生成的内容
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            system_prompt = self.STYLE_PROMPTS.get(
                config.style,
                self.STYLE_PROMPTS[ScriptStyle.COMMENTARY]
            )
            user_prompt = self._build_prompt(topic, config)

            response = client.chat.completions.create(
                model=config.model or "gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=config.temperature if hasattr(config, 'temperature') else 0.7,
                max_tokens=2000,
            )

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
        """
        生成解说文案（快捷方法）

        Args:
            topic: 解说主题
            duration: 目标时长（秒）
            tone: 语气
        """
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
        """
        生成独白文案（快捷方法）

        Args:
            context: 场景/情境描述
            emotion: 情感（如：惆怅、欣喜、思念）
            duration: 目标时长（秒）
        """
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
        keywords: Optional[List[str]] = None,
    ) -> GeneratedScript:
        """
        生成爆款文案（快捷方法）

        Args:
            topic: 主题
            duration: 目标时长（秒）
            keywords: 必须包含的关键词
        """
        config = ScriptConfig(
            style=ScriptStyle.VIRAL,
            tone=VoiceTone.EXCITED,
            target_duration=duration,
            include_hook=True,
            keywords=keywords or [],
        )
        return self.generate(topic, config)

    def _build_prompt(self, topic: str, config: ScriptConfig) -> str:
        """构建用户提示词"""
        parts = [f"请为以下主题生成视频文案：\n\n{topic}\n"]

        # 字数要求
        parts.append(f"\n字数要求：约 {config.target_words} 字（适合 {config.target_duration:.0f} 秒视频）")

        # 语气要求
        tone_map = {
            VoiceTone.NEUTRAL: "中性、客观",
            VoiceTone.EXCITED: "兴奋、激动",
            VoiceTone.CALM: "平静、舒缓",
            VoiceTone.MYSTERIOUS: "神秘、悬疑",
            VoiceTone.EMOTIONAL: "情感、深情",
            VoiceTone.HUMOROUS: "幽默、轻松",
        }
        parts.append(f"语气风格：{tone_map.get(config.tone, '中性')}")

        # 开头钩子
        if config.include_hook:
            parts.append("\n要求：开头3秒必须有吸引力的「钩子」，能立刻抓住观众注意力")

        # 行动号召
        if config.include_cta:
            parts.append("结尾需要有行动号召（如：点赞、关注、评论）")

        # 关键词
        if config.keywords:
            parts.append(f"\n必须自然融入以下关键词：{', '.join(config.keywords)}")

        # 格式要求
        parts.append("""
输出格式：
1. 直接输出文案内容，不要有标题或解释
2. 用空行分隔段落
3. 每段适合配合一个画面场景""")

        return "\n".join(parts)

    def _parse_response(
        self,
        content: str,
        config: ScriptConfig,
    ) -> GeneratedScript:
        """解析 LLM 响应"""
        # 清理内容
        content = content.strip()

        # 分段
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        # 计算每段时长
        total_words = len(content.replace(' ', '').replace('\n', ''))

        segments = []
        current_time = 0.0

        for i, para in enumerate(paragraphs):
            para_words = len(para.replace(' ', ''))
            para_duration = para_words / config.words_per_second

            segment = ScriptSegment(
                content=para,
                start_time=current_time,
                duration=para_duration,
                scene_hint=f"场景 {i + 1}",
            )
            segments.append(segment)
            current_time += para_duration

        # 提取钩子（第一段或第一句）
        hook = ""
        if segments:
            first = segments[0].content
            if '。' in first:
                hook = first.split('。')[0] + '。'
            else:
                hook = first

        return GeneratedScript(
            content=content,
            segments=segments,
            style=config.style,
            word_count=total_words,
            estimated_duration=total_words / config.words_per_second,
            hook=hook,
            keywords=config.keywords,
        )

    def split_to_captions(
        self,
        script: GeneratedScript,
        _max_chars: int = 20,  # reserved for char-based splitting (not yet used)
    ) -> List[Dict[str, Any]]:
        """
        将文案拆分为字幕

        Args:
            script: 生成的文案
            max_chars: 每条字幕最大字数

        Returns:
            字幕列表，每个包含 text, start, duration
        """
        import re

        captions = []

        for segment in script.segments:
            # 按标点拆分
            sentences = re.split(r'([。！？，；])', segment.content)

            current_start = segment.start_time
            segment_duration = segment.duration
            segment_words = len(segment.content.replace(' ', ''))

            current_text = ""
            for i, part in enumerate(sentences):
                if not part:
                    continue

                # 如果是标点，添加到当前文本
                if part in '。！？，；':
                    current_text += part

                    if len(current_text) > 5:  # 至少5个字才生成字幕
                        word_count = len(current_text)
                        duration = (word_count / max(segment_words, 1)) * segment_duration

                        captions.append({
                            "text": current_text,
                            "start": current_start,
                            "duration": duration,
                        })

                        current_start += duration
                        current_text = ""
                else:
                    current_text += part

            # 处理剩余文本
            if current_text.strip():
                word_count = len(current_text)
                duration = (word_count / max(segment_words, 1)) * segment_duration

                captions.append({
                    "text": current_text,
                    "start": current_start,
                    "duration": max(duration, 0.5),
                })

        return captions


# =========== 便捷函数 ===========

def generate_script(
    topic: str,
    style: ScriptStyle = ScriptStyle.COMMENTARY,
    duration: float = 60.0,
    use_llm_manager: bool = True,
    api_key: Optional[str] = None,
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
