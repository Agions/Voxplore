"""Response parsing utilities for script generation."""

import re
from typing import Any

from ..script_models import GeneratedScript, ScriptConfig, ScriptSegment


def parse_response(content: str, config: ScriptConfig) -> GeneratedScript:
    """解析 LLM 响应"""
    # 清理内容
    content = content.strip()

    # 分段
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    # 计算每段时长
    total_words = len(content.replace(" ", "").replace("\n", ""))

    segments = []
    current_time = 0.0

    for i, para in enumerate(paragraphs):
        para_words = len(para.replace(" ", ""))
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
        if "。" in first:
            hook = first.split("。")[0] + "。"
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


def parse_batch_response(
    content: str,
    batch: list[tuple[str, ScriptConfig]],
) -> list[GeneratedScript]:
    """
    解析批量生成的响应
    """
    content = content.strip()

    scripts = []
    for i, (_topic, config) in enumerate(batch):
        segment = extract_segment(content, i + 1, config)
        if segment:
            script = parse_response(segment, config)
        else:
            script = parse_response(content if i == 0 else "", config)
        scripts.append(script)

    return scripts


def extract_segment(
    content: str,
    segment_num: int,
    config: ScriptConfig,
) -> str:
    """
    从批量响应中提取指定段落
    """
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


def split_to_captions(
    script: GeneratedScript,
    _max_chars: int = 20,  # reserved for char-based splitting (not yet used)
) -> list[dict[str, Any]]:
    """
    将文案拆分为字幕

    Args:
        script: 生成的文案
        max_chars: 每条字幕最大字数

    Returns:
        字幕列表，每个包含 text, start, duration
    """
    captions = []

    for segment in script.segments:
        # 按标点拆分
        sentences = re.split(r"([。！？，；])", segment.content)

        current_start = segment.start_time
        segment_duration = segment.duration
        segment_words = len(segment.content.replace(" ", ""))

        current_text = ""
        for _i, part in enumerate(sentences):
            if not part:
                continue

            # 如果是标点，添加到当前文本
            if part in "。！？，；":
                current_text += part

                if len(current_text) > 5:  # 至少5个字才生成字幕
                    word_count = len(current_text)
                    duration = (word_count / max(segment_words, 1)) * segment_duration

                    captions.append(
                        {
                            "text": current_text,
                            "start": current_start,
                            "duration": duration,
                        }
                    )

                    current_start += duration
                    current_text = ""
            else:
                current_text += part

        # 处理剩余文本
        if current_text.strip():
            word_count = len(current_text)
            duration = (word_count / max(segment_words, 1)) * segment_duration

            captions.append(
                {
                    "text": current_text,
                    "start": current_start,
                    "duration": max(duration, 0.5),
                }
            )

    return captions
