"""
SceneFab v2.2 解说生成流水线

v2.2 重构后, 旧 scene_pipeline.py + 各 Step 模块已删除 (commit 287b050 + R2).
本包仅导出 v2.2 解说生成状态机 (NarrationStateMachine) 及其上下文/步骤.
"""

from .narration import (
    PLATFORM_SPECS,
    NarrationConfig,
    NarrationContext,
    NarrationState,
    NarrationStateMachine,
    NarrationStyle,
    Persona,
    Platform,
    StepResult,
    TransitionReason,
    register_assembly_steps,
    register_default_steps,
    register_evaluation_steps,
    register_understanding_steps,
)

__all__ = [
    "PLATFORM_SPECS",
    "NarrationConfig",
    "NarrationContext",
    "NarrationState",
    "NarrationStateMachine",
    "NarrationStyle",
    "Persona",
    "Platform",
    "StepResult",
    "TransitionReason",
    "register_default_steps",
    "register_understanding_steps",
    "register_evaluation_steps",
    "register_assembly_steps",
]
