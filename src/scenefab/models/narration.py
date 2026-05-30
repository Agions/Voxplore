#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
解说/叙事数据模型

包含解说风格、情感类型和解说块。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class NarrationStyle(Enum):
    """解说风格"""
    HEALING = "healing"      # 治愈
    MYSTERIOUS = "mysterious"  # 悬疑
    INSPIRATIONAL = "inspirational"  # 励志
    NOSTALGIC = "nostalgic"    # 怀旧
    ROMANTIC = "romantic"      # 浪漫
    HUMOROUS = "humorous"      # 幽默
    DOCUMENTARY = "documentary"  # 纪录片


class EmotionType(Enum):
    """情感类型"""
    CALM = "calm"
    EXCITED = "excited"
    EMOTIONAL = "emotional"
    MYSTERIOUS = "mysterious"
    NEUTRAL = "neutral"


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