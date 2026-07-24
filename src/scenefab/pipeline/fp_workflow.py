#!/usr/bin/env python3
"""First-person narration workflow definitions and validation rules."""

from dataclasses import dataclass
import re

THIRD_PERSON_LEAK_PATTERNS = (
    r"只见男主",
    r"只见女主",
    r"此时主角",
    r"男主角",
    r"女主角",
    r"画面中的他",
    r"画面中的她",
    r"旁白说道",
    r"镜头转到",
)


@dataclass(frozen=True, slots=True)
class WorkflowStage:
    """A reusable production workflow stage."""

    id: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class ScriptRule:
    """A script constraint for first-person narration."""

    label: str
    value: str


FIRST_PERSON_WORKFLOW = (
    WorkflowStage("source_review", "素材审片", "标记人物目标、危险处境和强情绪镜头"),
    WorkflowStage("conflict_map", "冲突拆解", "提取开局误会、反转、代价和悬念点"),
    WorkflowStage("hook", "第一人称钩子", "3 秒内用我视角抛出选择、危机或结果"),
    WorkflowStage("beat_pacing", "爽点节奏", "每 6-10 秒推进一次信息、情绪或反转"),
    WorkflowStage("voice_subtitle", "配音字幕", "口播、字幕和画面动作逐句对齐"),
    WorkflowStage("publish_review", "发布复盘", "记录完播、跳出点和下一版钩子假设"),
)

FIRST_PERSON_SCRIPT_RULES = (
    ScriptRule("视角", "我是谁、我想要什么、我怕失去什么"),
    ScriptRule("开头", "3 秒内给出冲突或结果预告"),
    ScriptRule("节奏", "6-10 秒一次新信息、强情绪或反转"),
    ScriptRule("结尾", "悬念、代价、反杀或下一集钩子"),
)

FIRST_PERSON_QUALITY_GATES = (
    "开头 3 秒出现人物目标、危机或结果预告",
    "每 6-10 秒至少一次信息推进或情绪变化",
    "第一人称主语清晰，不频繁切换叙述身份",
    "字幕与配音偏差小于 50ms",
    "无声观看时字幕也能理解主要冲突",
)


def numbered_workflow(
    stages: tuple[WorkflowStage, ...] = FIRST_PERSON_WORKFLOW,
) -> tuple[tuple[str, WorkflowStage], ...]:
    """Return stages with stable 01-based display numbers."""
    return tuple((f"{index:02d}", stage) for index, stage in enumerate(stages, start=1))


def validate_first_person_script(script_text: str) -> list[str]:
    """校验解说文案是否符合第一人称规范。

    Returns:
        包含所有不合规问题描述的列表；若为空则表示完全合规。
    """
    violations: list[str] = []

    if not script_text or not script_text.strip():
        return ["文案内容为空"]

    # 1. 第一人称视角主语检查
    if "我" not in script_text:
        violations.append("文案缺少第一人称主语 '我'，请确保以主角第一人称独白展开")

    # 2. 第三人称混入泄漏检测
    for pattern in THIRD_PERSON_LEAK_PATTERNS:
        if re.search(pattern, script_text):
            violations.append(f"发现第三人称旁白词汇汇出: '{pattern.replace('r', '')}'，必须使用第一人称主角视角")

    # 3. 黄金 Hook 校验（前 30 字内是否有危机/反转悬念）
    first_30_chars = script_text[:30]
    hook_keywords = ("我", "没想", "居然", "死", "逃", "发现", "居然", "如果", "以为", "陷阱", "最后", "竟然")
    if not any(kw in first_30_chars for kw in hook_keywords):
        violations.append("开头 3 秒Hook弱：建议前 30 字内直接包含冲突、危机或悬念结果")

    return violations


def build_first_person_system_prompt(character_name: str = "主角", style_name: str = "短剧高能解说") -> str:
    """构建严格遵循第一人称解说规范的 LLM System Prompt。"""
    return f"""你是一位资深短剧/影视第一人称解说创作者，当前代入的角色是【{character_name}】。

解说风格：{style_name}

【核心撰写规范】：
1. **视角锁死**：必须全程以【{character_name}】的第一人称视角("我")讲述。严禁使用"只见男主"、"此时主角"、"画面中"等第三人称旁白词汇。
2. **黄金 3 秒 Hook**：开场前 1-2 句话（3 秒内）必须直接抛出重大危机、反转结果或艰难选择，吸引观众驻留。
3. **内心 OS 情绪渲染**：结合画面镜头，重点描写我当时的内心独白（OS）、恐惧、愤怒或复仇快感。
4. **爽点与节奏**：每 6-10 秒必须推动一次剧情进展、信息暴露或情感反转。
5. **简洁口语化**：使用适合短视频口播的短句，剔除所有冗长繁琐的环境描述。
"""


__all__ = [
    "FIRST_PERSON_QUALITY_GATES",
    "FIRST_PERSON_SCRIPT_RULES",
    "FIRST_PERSON_WORKFLOW",
    "THIRD_PERSON_LEAK_PATTERNS",
    "ScriptRule",
    "WorkflowStage",
    "build_first_person_system_prompt",
    "numbered_workflow",
    "validate_first_person_script",
]
