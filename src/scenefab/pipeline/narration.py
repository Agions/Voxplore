"""
v2.2 解说生成状态机 — Phase 1 骨架 + Phase 2/3/4 真实实现

公开 API:
- NarrationContext / Persona / Platform / NarrationStyle / Bridge / BridgeType
- NarrationState / NarrationStateMachine / NarrationConfig / StepResult
- NarrationEvaluator / EvalResult / DimensionScore (Phase 3)
- register_default_steps (Phase 1 骨架 Step)
- register_phase2_steps (Phase 2 真实实现 — 替换 UNDERSTAND/STORYGRAPH/DRAFT)
- register_phase3_steps (Phase 3 真实实现 — 替换 EVALUATE/HOOK_REWRITE)
- register_phase4_steps (Phase 4 真实实现 — 替换 TTS_LENGTH_ADJUST/TTS/ASSEMBLE)

v2.2 决策: 见 docs/adr/007-narration-state-machine.md
"""

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
from .narration_steps_phase2 import (
    _build_narration_prompt,
    draft_step,
    register_phase2_steps,
    storygraph_step,
    understand_step,
)
from .narration_steps_phase3 import (
    evaluate_step as evaluate_step_phase3,
)
from .narration_steps_phase3 import (
    hook_rewrite_step as hook_rewrite_step_phase3,
)
from .narration_steps_phase3 import (
    register_phase3_steps,
)
from .narration_steps_phase4 import (
    assemble_step,
    probe_audio_duration,
    register_phase4_steps,
    tts_length_adjust_step,
    tts_step,
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
    "register_phase2_steps",
    "register_phase3_steps",
    "register_phase4_steps",
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
