"""
SceneFab 爆款评分数据模型

包含五维评分模型的所有数据结构：钩子评分、情绪曲线评分、
信息密度评分、节奏匹配评分、互动设计评分和综合结果。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HookScore:
    """开篇钩子评分"""

    score: float  # 0-100
    hook_type: str  # "conflict", "suspense", "result_first", "question", "shock"
    detected_elements: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class EmotionCurveScore:
    """情绪曲线评分"""

    score: float  # 0-100
    emotion_points: list[dict[str, Any]] = field(default_factory=list)
    curve_type: str = (
        "wave"  # "rising", "falling", "wave", "climax_early", "climax_late"
    )
    peak_timestamps: list[float] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class InformationDensityScore:
    """信息密度评分"""

    score: float  # 0-100
    density_map: list[dict[str, Any]] = field(default_factory=list)  # 每 10 秒的密度
    average_density: float = 0.0
    high_density_segments: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class RhythmMatchScore:
    """节奏匹配评分"""

    score: float  # 0-100
    current_bpm: float = 0.0
    target_bpm: float = 0.0
    rhythm_type: str = "medium"  # "fast", "medium", "slow"
    match_ratio: float = 0.0
    suggestions: list[str] = field(default_factory=list)


@dataclass
class InteractionDesignScore:
    """互动设计评分"""

    score: float  # 0-100
    cta_count: int = 0
    cta_types: list[str] = field(default_factory=list)
    question_count: int = 0
    open_ended_questions: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ViralScoreResult:
    """爆款评分结果"""

    total_score: float  # 0-100
    hook_score: HookScore
    emotion_curve_score: EmotionCurveScore
    information_density_score: InformationDensityScore
    rhythm_match_score: RhythmMatchScore
    interaction_design_score: InteractionDesignScore
    grade: str  # "S", "A", "B", "C", "D"
    recommendations: list[str] = field(default_factory=list)
    assessment_time: str = ""
    assessor_version: str = "1.0.0"
