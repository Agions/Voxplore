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
    ):
        """
        初始化文案生成器

        Args:
            api_key: OpenAI API Key（传统方式）
            use_llm_manager: 是否使用 LLMManager（新架构）
            llm_config: LLM 配置字典
            llm_config_file: LLM 配置文件路径
        """
        self.use_llm_manager = use_llm_manager
        self.llm_manager: Optional[LLMManager] = None

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

            messages = []
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            response = client.chat.completions.create(
                model=config.model or "gpt-4",
                messages=messages,
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
        max_chars: int = 20,
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


def demo_generate():
    """演示文案生成"""
    # 使用新架构
    try:
        print("\n" + "=" * 50)
        print("🎬 Voxplore - 文案生成测试")
        print("=" * 50)

        generator = ScriptGenerator(use_llm_manager=True)

        # 生成解说文案
        print("\n生成解说文案...")
        script = generator.generate_commentary(
            topic="分析《流浪地球》系列电影中的科学设定是否合理",
            duration=60,
        )

        print("=" * 50)
        print("【解说文案】")
        print("=" * 50)
        print(f"字数: {script.word_count}")
        print(f"预估时长: {script.estimated_duration:.1f}秒")
        print(f"提供商: {script.provider_used}")
        print(f"钩子: {script.hook}")
        print("-" * 50)
        print(script.content)
        print()

    except Exception as e:
        logger.error(f"生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    demo_generate()
