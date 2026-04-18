#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语音生成数据模型

定义语音合成相关的枚举和数据结构。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VoiceStyle(Enum):
    """配音风格"""
    NARRATION = "narration"        # 旁白/解说
    CONVERSATIONAL = "conversational"  # 对话
    NEWSCAST = "newscast"          # 新闻播报
    CHEERFUL = "cheerful"          # 欢快
    SAD = "sad"                    # 悲伤
    ANGRY = "angry"                # 愤怒
    FEARFUL = "fearful"            # 恐惧
    WHISPERING = "whispering"      # 耳语
    SHOUTING = "shouting"          # 大喊


class VoiceGender(Enum):
    """声音性别"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class VoiceConfig:
    """配音配置"""
    # 声音选择
    voice_id: str = ""             # 声音 ID(不同提供商格式不同)
    gender: VoiceGender = VoiceGender.FEMALE

    # 风格
    style: VoiceStyle = VoiceStyle.NARRATION
    style_degree: float = 1.0      # 风格强度 (0.5-2.0)

    # 语速语调
    rate: float = 1.0              # 语速 (0.5-2.0)
    pitch: float = 1.0             # 音调 (0.5-2.0)
    volume: float = 1.0            # 音量 (0.0-1.0)

    # 输出格式
    output_format: str = "mp3"     # mp3, wav, ogg
    sample_rate: int = 24000       # 采样率

    # 语言
    language: str = "zh-CN"

    # F5-TTS 音色克隆参数
    ref_audio: str = ""        # 参考音频路径(15-30 秒人声)
    ref_text: str = ""         # 参考音频对应的文本


@dataclass
class VoiceInfo:
    """声音信息"""
    id: str
    name: str
    gender: VoiceGender
    language: str
    styles: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class GeneratedVoice:
    """生成的配音"""
    audio_path: str                # 音频文件路径
    duration: float                # 时长(秒)
    text: str                      # 原始文本
    voice_id: str                  # 使用的声音

    # 元数据
    sample_rate: int = 24000
    format: str = "mp3"
    start_time: float = 0.0        # 片段起始时间(用于批量生成)
    sentence_timestamps: List[Dict[str, Any]] = None  # 句子级时间戳

    def __post_init__(self):
        if self.sentence_timestamps is None:
            self.sentence_timestamps = []


__all__ = [
    "VoiceStyle",
    "VoiceGender",
    "VoiceConfig",
    "VoiceInfo",
    "GeneratedVoice",
]
