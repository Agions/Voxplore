#!/usr/bin/env python3

"""
解说/叙事数据模型

包含解说风格、情感类型和解说块。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class NarrationStyle(Enum):
    """解说风格"""

    HEALING = "healing"  # 治愈
    MYSTERIOUS = "mysterious"  # 悬疑
    INSPIRATIONAL = "inspirational"  # 励志
    NOSTALGIC = "nostalgic"  # 怀旧
    ROMANTIC = "romantic"  # 浪漫
    HUMOROUS = "humorous"  # 幽默
    DOCUMENTARY = "documentary"  # 纪录片


class EmotionType(str, Enum):
    """情感类型（统一权威定义）

    涵盖所有场景：解说、API、第一人称独白。
    继承 str 以保证 API JSON 序列化兼容性。
    """

    # 基础情感（来自原 narration.py）
    NEUTRAL = "neutral"
    CALM = "calm"
    EXCITED = "excited"
    EMOTIONAL = "emotional"
    MYSTERIOUS = "mysterious"

    # 扩展情感（来自 monologue.py）
    SAD = "sad"
    HAPPY = "happy"
    ANGRY = "angry"
    TENDER = "tender"

    # API 情感（来自 api/schemas/models.py）
    HEALING = "healing"
    SUSPENSE = "suspense"
    MOTIVATIONAL = "motivational"
    NOSTALGIC = "nostalgic"
    ROMANTIC = "romantic"


@dataclass(slots=True)
class NarrationBlock:
    """解说块"""

    text: str
    start_time: float
    end_time: float
    emotion: EmotionType = EmotionType.NEUTRAL
    style: NarrationStyle = NarrationStyle.DOCUMENTARY

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "emotion": self.emotion.value,
            "style": self.style.value,
        }


__all__ = ["NarrationStyle", "EmotionType", "NarrationBlock"]
