"""
SceneFab v2.2 解说生成流水线

v2.2 重构后, 旧 scene_pipeline.py + 各 Step 模块已删除 (commit 287b050 + R2).
本包仅导出 v2.2 解说生成状态机 (NarrationStateMachine) 及其上下文/步骤.
"""

from .fp_workflow import (
    FIRST_PERSON_QUALITY_GATES,
    FIRST_PERSON_SCRIPT_RULES,
    FIRST_PERSON_WORKFLOW,
    ScriptRule,
    WorkflowStage,
    numbered_workflow,
)
from .narration.engine import (
    PLATFORM_SPECS,
    NarrationConfig,
    NarrationContext,
    NarrationState,
    NarrationStateMachine,
    Persona,
    Platform,
    ProductionStyle,
    StepResult,
    TransitionReason,
    register_assembly_steps,
    register_default_steps,
    register_evaluation_steps,
    register_understanding_steps,
)

__all__ = [
    "FIRST_PERSON_QUALITY_GATES",
    "FIRST_PERSON_SCRIPT_RULES",
    "FIRST_PERSON_WORKFLOW",
    "PLATFORM_SPECS",
    "NarrationConfig",
    "NarrationContext",
    "NarrationState",
    "NarrationStateMachine",
    "ProductionStyle",
    "Persona",
    "Platform",
    "ScriptRule",
    "StepResult",
    "TransitionReason",
    "WorkflowStage",
    "numbered_workflow",
    "register_default_steps",
    "register_understanding_steps",
    "register_evaluation_steps",
    "register_assembly_steps",
]
