"""
SceneFab 爆款五维评分模块

功能：
1. 前 3 秒钩子检测（LLM 评估）
2. 情绪曲线可视化（波形图）
3. 信息密度热力图（每 10 秒有效信息量）
4. 节奏匹配度（当前节奏 vs 平台最优节奏）
5. 互动设计评分（CTA/开放式问题检测）

评分公式：
爆款评分 = 0.30 × 开篇钩子分 + 0.25 × 情绪曲线分 + 0.20 × 信息密度分 + 0.15 × 节奏匹配分 + 0.10 × 互动设计分
"""

from scenefab.services.viral.calculator import (
    ViralScoreCalculator,
    calculate_viral_score,
)
from scenefab.services.viral.models import (
    EmotionCurveScore,
    HookScore,
    InformationDensityScore,
    InteractionDesignScore,
    RhythmMatchScore,
    ViralScoreResult,
)

__all__ = [
    "EmotionCurveScore",
    "HookScore",
    "InformationDensityScore",
    "InteractionDesignScore",
    "RhythmMatchScore",
    "ViralScoreCalculator",
    "ViralScoreResult",
    "calculate_viral_score",
]
