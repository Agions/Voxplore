#!/usr/bin/env python3
"""First-person narration workflow definitions."""

from dataclasses import dataclass


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


__all__ = [
    "FIRST_PERSON_QUALITY_GATES",
    "FIRST_PERSON_SCRIPT_RULES",
    "FIRST_PERSON_WORKFLOW",
    "ScriptRule",
    "WorkflowStage",
    "numbered_workflow",
]
