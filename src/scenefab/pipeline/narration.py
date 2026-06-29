"""
v2.2 解说生成状态机 — Phase 1 骨架 + Phase 2/3/4 真实实现

公开 API:
- NarrationContext / Persona / Platform / NarrationStyle / Bridge / BridgeType
- NarrationState / NarrationStateMachine / NarrationConfig / StepResult
- NarrationEvaluator / EvalResult / DimensionScore (Phase 3)
- register_default_steps (Phase 1 骨架 Step)
- register_understanding_steps (Phase 2 真实实现 — 替换 UNDERSTAND/STORYGRAPH/DRAFT)
- register_evaluation_steps (Phase 3 真实实现 — 替换 EVALUATE/HOOK_REWRITE)
- register_assembly_steps (Phase 4 真实实现 — 替换 TTS_LENGTH_ADJUST/TTS/ASSEMBLE)
"""

from .assembly_steps import (
    assemble_step,
    probe_audio_duration,
    register_assembly_steps,
    tts_length_adjust_step,
    tts_step,
)
from .evaluation_steps import (
    evaluate_step as evaluate_step_phase3,
)
from .evaluation_steps import (
    hook_rewrite_step as hook_rewrite_step_phase3,
)
from .evaluation_steps import (
    register_evaluation_steps,
)
from .narration_context import (
    PLATFORM_SPECS,
    Bridge,
    BridgeType,
    FewShot,
    HistorySegment,
    NarrationContext,
    NarrationStyle,
    Persona,
    Platform,
    PlatformSpec,
)
from .narration_evaluator import (
    DimensionScore,
    EvalResult,
    NarrationEvaluator,
)
from .narration_state_machine import (
    NarrationConfig,
    NarrationState,
    NarrationStateMachine,
    StateTransition,
    StepResult,
    TransitionReason,
)
from .narration_steps import register_default_steps
from .understanding_steps import (
    _build_narration_prompt,
    draft_step,
    register_understanding_steps,
    storygraph_step,
    understand_step,
)

__all__ = [
    # Context
    "Bridge",
    "BridgeType",
    "FewShot",
    "HistorySegment",
    "NarrationContext",
    "NarrationStyle",
    "Persona",
    "Platform",
    "PLATFORM_SPECS",
    "PlatformSpec",
    # State machine
    "NarrationConfig",
    "NarrationState",
    "NarrationStateMachine",
    "StateTransition",
    "StepResult",
    "TransitionReason",
    # Evaluator
    "DimensionScore",
    "EvalResult",
    "NarrationEvaluator",
    # Steps
    "register_default_steps",
    "register_understanding_steps",
    "register_evaluation_steps",
    "register_assembly_steps",
    "understand_step",
    "storygraph_step",
    "draft_step",
    "evaluate_step_phase3",
    "hook_rewrite_step_phase3",
    "tts_length_adjust_step",
    "tts_step",
    "assemble_step",
    "probe_audio_duration",
    "_build_narration_prompt",
]
