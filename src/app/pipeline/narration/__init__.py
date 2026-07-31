"""SceneFab v2.2 解说生成状态机子包。

公开 API:
- NarrationStateMachine / NarrationConfig / NarrationContext
- StepResult / NarrationState / TransitionReason
- NarrationEvaluator / EvalResult / DimensionScore
- register_default_steps / register_understanding_steps / register_evaluation_steps
- register_assembly_steps
"""

from .engine import (
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
from .evaluator import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    EvalResult,
    NarrationEvaluator,
)
from .steps import accept_step, ingest_step, reject_step

__all__ = [
    "NarrationConfig",
    "NarrationContext",
    "NarrationState",
    "NarrationStateMachine",
    "Persona",
    "Platform",
    "ProductionStyle",
    "StepResult",
    "TransitionReason",
    "register_assembly_steps",
    "register_default_steps",
    "register_understanding_steps",
    "register_evaluation_steps",
    "DIMENSION_WEIGHTS",
    "DimensionScore",
    "EvalResult",
    "NarrationEvaluator",
    "ingest_step",
    "reject_step",
    "accept_step",
]
