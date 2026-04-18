#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Monologue 数据模型

定义 AI 第一人称独白视频项目的数据结构：
- MonologueStyle: 独白风格枚举
- EmotionType: 情感类型枚举
- MonologueSegment: 独白片段

注意：MonologueProject 定义在 monologue_maker.py 中（需要继承 BaseProject）
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict


class MonologueStyle(Enum):
    """独白风格"""
    MELANCHOLIC = "melancholic"    # 惆怅/忧郁
    INSPIRATIONAL = "inspirational"  # 励志/向上
    ROMANTIC = "romantic"          # 浪漫/温馨
    MYSTERIOUS = "mysterious"      # 神秘/悬疑
    NOSTALGIC = "nostalgic"        # 怀旧/追忆
    PHILOSOPHICAL = "philosophical"  # 哲思/沉思
    HEALING = "healing"            # 治愈/温暖


class EmotionType(Enum):
    """情感类型"""
    NEUTRAL = "neutral"
    SAD = "sad"
    HAPPY = "happy"
    ANGRY = "angry"
    CALM = "calm"
    EXCITED = "excited"
    TENDER = "tender"


@dataclass
class MonologueSegment:
    """独白片段"""
    script: str                    # 独白文案
    emotion: EmotionType           # 情感

    # 视频片段
    video_start: float
    video_end: float

    # 音频
    audio_path: str = ""
    audio_duration: float = 0.0
    sentence_timestamps: List[Dict] = field(default_factory=list)  # EdgeTTS 句子级时间戳

    # 字幕
    captions: List[Dict] = field(default_factory=list)


__all__ = [
    "MonologueStyle",
    "EmotionType",
    "MonologueSegment",
]
