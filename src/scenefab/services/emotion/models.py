"""
SceneFab 情绪点检测数据模型

包含场景类型、情绪标签、推荐节奏等枚举和数据结构定义。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SceneType(str, Enum):
    """场景类型"""

    ACTION = "action"  # 动作场景
    DIALOGUE = "dialogue"  # 对话场景
    REVERSAL = "reversal"  # 反转场景
    CLIMAX = "climax"  # 高潮场景
    RESOLUTION = "resolution"  # 结局场景
    TRANSITION = "transition"  # 过渡场景


class EmotionLabel(str, Enum):
    """情绪标签"""

    TENSION = "tension"  # 紧张
    JOY = "joy"  # 愉快
    SADNESS = "sadness"  # 悲伤
    SURPRISE = "surprise"  # 惊讶
    FEAR = "fear"  # 恐惧
    ANGER = "anger"  # 愤怒
    NEUTRAL = "neutral"  # 中性


class RecommendedPace(str, Enum):
    """推荐节奏"""

    FAST = "fast"  # 快节奏
    NORMAL = "normal"  # 正常节奏
    SLOW = "slow"  # 慢节奏


@dataclass
class SceneEmotion:
    """场景情绪数据"""

    timestamp: float  # 时间戳（秒）
    scene_type: SceneType  # 场景类型
    emotion_label: EmotionLabel  # 情绪标签
    intensity: float  # 情绪强度 0.0-1.0
    recommended_pace: RecommendedPace  # 推荐节奏
    confidence: float  # 置信度 0.0-1.0
    description: str = ""  # 场景描述
    audio_features: dict[str, Any] = field(default_factory=dict)  # 音频特征
    visual_features: dict[str, Any] = field(default_factory=dict)  # 视觉特征


@dataclass
class EmotionDetectionResult:
    """情绪检测结果"""

    video_path: str
    duration: float  # 视频时长（秒）
    scene_emotions: list[SceneEmotion] = field(default_factory=list)
    emotion_curve: list[dict[str, Any]] = field(default_factory=list)  # 情绪曲线数据
    peak_moments: list[dict[str, Any]] = field(default_factory=list)  # 情绪高峰时刻
    detection_time: str = ""
    detector_version: str = "1.0.0"
