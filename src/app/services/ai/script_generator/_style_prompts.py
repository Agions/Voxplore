"""Style prompt templates and tone mappings for script generation."""

from ..script_models import ScriptStyle, VoiceTone

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

# 语气映射
TONE_MAP = {
    VoiceTone.NEUTRAL: "中性、客观",
    VoiceTone.EXCITED: "兴奋、激动",
    VoiceTone.CALM: "平静、舒缓",
    VoiceTone.MYSTERIOUS: "神秘、悬疑",
    VoiceTone.EMOTIONAL: "情感、深情",
    VoiceTone.HUMOROUS: "幽默、轻松",
}

# ── v2.5.0 多视频策略提示词 ─────────────────────────────────────
# 随 multi_strategy 拼接到用户提示词末尾，引导 LLM 理解「这是哪种场景」。
STRATEGY_INSTRUCTIONS: dict[str, str] = {
    "single": (
        "\n\n【单视频场景】此为单一原始视频，请按其本身的故事走向和画面节奏生成独立解说。"
    ),
    "concat": (
        "\n\n【拼接场景】多段原始视频将被顺次拼接为一条成片。"
        "请生成连贯的叙事线，确保段与段之间的过渡自然、不重复前情。"
    ),
    "batch": (
        "\n\n【批量独立场景】多个原始视频之间没有剧情关联，请为每一个独立生成一份解说。"
        "每份文案须自我闭环，不依赖其他视频的前情。"
    ),
    "series": (
        "\n\n【整季系列场景】此为同一剧集的其中一集，全季共享一致的设定与人物体系。"
        "请严格使用【系列背景】中给出的人物名称、世界观与剧情走向，"
        "不要重新捏造人物称呼或颠覆既有人设。"
    ),
}


def series_context_block(series_ctx) -> str:
    """将 :class:`SeriesContext` 渲染为 LLM 友好的提示词块。

    仅当 strategy == ``"series"`` 且 ``series_ctx`` 非空时才调用。
    返回纯文本，可直接拼到 ``build_prompt`` 末尾。
    """
    if series_ctx is None:
        return ""

    lines: list[str] = ["\n\n【系列背景（v2.5.0）】"]
    if series_ctx.series_title:
        lines.append(f"- 剧名：{series_ctx.series_title}")
    if series_ctx.genre:
        lines.append(f"- 题材：{series_ctx.genre}")
    if series_ctx.total_episodes > 0:
        lines.append(f"- 总集数：{series_ctx.total_episodes}")
    if series_ctx.world_setting:
        lines.append(f"- 世界观设定：{series_ctx.world_setting}")
    if series_ctx.shared_characters:
        chars = "、".join(series_ctx.shared_characters)
        lines.append(f"- 共享人物：{chars}")
    if series_ctx.shared_plot:
        lines.append(f"- 全季剧情主线：{series_ctx.shared_plot}")
    return "\n".join(lines)
