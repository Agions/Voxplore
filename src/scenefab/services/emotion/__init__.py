"""
SceneFab 情绪点检测模块

功能：
1. 多模态情绪分析（音频 + 视觉）
2. 情绪锚点自动标记
3. 场景类型识别
4. 推荐节奏生成

输出数据结构：
SceneEmotion {
    timestamp: float,
    scene_type: "action" | "dialogue" | "reversal" | "climax" | "resolution",
    emotion_label: "tension" | "joy" | "sadness" | "surprise" | "neutral",
    intensity: 0.0 ~ 1.0,
    recommended_pace: "fast" | "normal" | "slow",
}
"""

from scenefab.services.emotion.detector import EmotionDetector, detect_emotions
from scenefab.services.emotion.models import (
    EmotionDetectionResult,
    EmotionLabel,
    RecommendedPace,
    SceneEmotion,
    SceneType,
)

__all__ = [
    "EmotionDetectionResult",
    "EmotionDetector",
    "EmotionLabel",
    "RecommendedPace",
    "SceneEmotion",
    "SceneType",
    "detect_emotions",
]
