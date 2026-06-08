"""Script generation for video narration blocks."""

import logging
from collections.abc import Callable

from ..models.narration import EmotionType, NarrationBlock, NarrationStyle
from ..models.video import VideoSegment

logger = logging.getLogger(__name__)


class ScriptGenerator:
    """解说文案生成器 V2"""

    STYLE_PROMPTS = {
        NarrationStyle.HEALING: "温暖治愈的风格，像朋友在耳边轻声诉说",
        NarrationStyle.MYSTERIOUS: "神秘悬疑的风格，营造紧张氛围",
        NarrationStyle.INSPIRATIONAL: "励志激昂的风格，充满正能量",
        NarrationStyle.NOSTALGIC: "怀旧平静的风格，回忆往事",
        NarrationStyle.ROMANTIC: "浪漫温柔的风格，表达深情",
        NarrationStyle.HUMOROUS: "幽默活泼的风格，让人轻松愉快",
        NarrationStyle.DOCUMENTARY: "沉稳纪录片的风格，客观叙述",
    }

    def __init__(self, llm_service=None):
        from ..services import get_ai_service_manager
        ai_service_manager = get_ai_service_manager()
        self.llm = llm_service or ai_service_manager.get_llm()

    def generate(
        self,
        segments: list[VideoSegment],
        context: str = "",
        emotion: EmotionType = EmotionType.NEUTRAL,
        style: NarrationStyle = NarrationStyle.DOCUMENTARY,
        progress_callback: Callable | None = None
    ) -> list[NarrationBlock]:
        if not self.llm:
            logger.warning("No LLM service available, using default script")
            return self._generate_default(len(segments))

        blocks = []
        total = len(segments)

        for i, seg in enumerate(segments):
            prompt = self._build_prompt(seg, context, emotion, style)

            try:
                result = self.llm.generate(
                    prompt=prompt,
                    system="你是一个专业的影视解说文案撰写师，擅长第一人称视角的叙事风格。"
                )

                if result:
                    text = result.strip()
                else:
                    text = self._get_default_text(i, style)
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}")
                text = self._get_default_text(i, style)

            blocks.append(NarrationBlock(
                text=text,
                start_time=seg.start_time,
                end_time=seg.end_time,
                emotion=emotion,
                style=style
            ))

            if progress_callback:
                progress_callback(i + 1, total)

        return blocks

    def _build_prompt(
        self,
        segment: VideoSegment,
        context: str,
        emotion: EmotionType,
        style: NarrationStyle
    ) -> str:
        duration = segment.end_time - segment.start_time
        style_hint = self.STYLE_PROMPTS.get(style, "")

        return f"""为以下视频片段撰写第一人称解说文案：

场景描述：{segment.description}
片段时长：约{duration:.0f}秒
情感基调：{emotion.value}
风格要求：{style_hint}
{f"背景上下文：{context}" if context else ""}

要求：
1. 第一人称"我"视角
2. {duration:.0f}秒时长，约{int(duration * 3)}个汉字
3. 符合指定风格和情感
4. 有画面感，像在现场一样叙述

解说文案："""

    def _generate_default(self, count: int) -> list[NarrationBlock]:
        texts = [
            "这是我记忆中最深刻的时刻。",
            "那时候的我，还不知道接下来会发生什么。",
            "回想起来，一切都是最好的安排。",
            "有些事情，只有自己知道。",
            "那些藏在心底的话，从未对人说起。",
        ]

        return [
            NarrationBlock(
                text=texts[i % len(texts)],
                start_time=i * 10.0,
                end_time=(i + 1) * 10.0,
                emotion=EmotionType.NEUTRAL,
                style=NarrationStyle.DOCUMENTARY
            )
            for i in range(count)
        ]

    def _get_default_text(self, index: int, style: NarrationStyle) -> str:
        defaults = {
            NarrationStyle.HEALING: "那一刻，温暖涌上心头。",
            NarrationStyle.MYSTERIOUS: "事情的真相，远比想象复杂。",
            NarrationStyle.INSPIRATIONAL: "只要坚持，一切皆有可能！",
            NarrationStyle.NOSTALGIC: "时光荏苒，回忆依旧。",
            NarrationStyle.ROMANTIC: "那一刻，心跳加速。",
            NarrationStyle.HUMOROUS: "没想到，事情会这样发展！",
            NarrationStyle.DOCUMENTARY: "这就是当时的情况。",
        }
        return defaults.get(style, "继续讲述...")
