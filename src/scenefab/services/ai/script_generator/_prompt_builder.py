"""Prompt construction helpers for script generation."""

from ..script_models import ScriptConfig
from ._style_prompts import TONE_MAP


def build_prompt(topic: str, config: ScriptConfig) -> str:
    """构建用户提示词"""
    parts = [f"请为以下主题生成视频文案：\n\n{topic}\n"]

    # 字数要求
    parts.append(
        f"\n字数要求：约 {config.target_words} 字（适合 {config.target_duration:.0f} 秒视频）"
    )

    # 语气要求
    parts.append(f"语气风格：{TONE_MAP.get(config.tone, '中性')}")

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


def build_batch_prompt(batch: list[tuple[str, ScriptConfig]]) -> str:
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
        parts.append(f"语气风格: {TONE_MAP.get(config.tone, '中性')}")

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
