#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 文案生成数据模型

定义文案生成相关的枚举和数据结构。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ScriptStyle(Enum):
    """文案风格"""
    COMMENTARY = "commentary"      # 解说风格（客观、信息密集）
    MONOLOGUE = "monologue"        # 独白风格（第一人称、情感化）
    NARRATION = "narration"        # 旁白风格（故事性、引导）
    VIRAL = "viral"                # 爆款风格（抓眼球、节奏快）
    EDUCATIONAL = "educational"    # 教育风格（清晰、有条理）


class VoiceTone(Enum):
    """语气"""
    NEUTRAL = "neutral"            # 中性
    EXCITED = "excited"            # 兴奋
    CALM = "calm"                  # 平静
    MYSTERIOUS = "mysterious"      # 神秘
    EMOTIONAL = "emotional"        # 情感化
    HUMOROUS = "humorous"          # 幽默


@dataclass
class ScriptConfig:
    """文案生成配置"""
    style: ScriptStyle = ScriptStyle.COMMENTARY
    tone: VoiceTone = VoiceTone.NEUTRAL

    # 时长控制
    target_duration: float = 60.0  # 目标时长（秒）
    words_per_second: float = 3.0  # 语速（每秒字数）

    # LLM 控制
    provider: Optional[str] = None  # 指定提供商 (qwen/kimi/glm5/openai)
    model: str = "default"           # 模型名称

    # 内容控制
    include_hook: bool = True      # 是否包含开头钩子
    include_cta: bool = False      # 是否包含行动号召

    # 语言
    language: str = "zh-CN"        # 语言

    # 关键词
    keywords: List[str] = field(default_factory=list)  # 必须包含的关键词

    @property
    def target_words(self) -> int:
        """目标字数"""
        return int(self.target_duration * self.words_per_second)


@dataclass
class ScriptSegment:
    """文案片段"""
    content: str                   # 文案内容
    start_time: float = 0.0        # 开始时间（秒）
    duration: float = 0.0          # 持续时间（秒）
    scene_hint: str = ""           # 画面提示
    emotion: str = "neutral"       # 情感标签


@dataclass
class GeneratedScript:
    """生成的文案"""
    content: str                   # 完整文案
    segments: List[ScriptSegment] = field(default_factory=list)  # 分段文案

    # 元数据
    style: ScriptStyle = ScriptStyle.COMMENTARY
    word_count: int = 0
    estimated_duration: float = 0.0
    provider_used: str = ""        # 使用的提供商

    # 爆款元素
    hook: str = ""                 # 开头钩子
    keywords: List[str] = field(default_factory=list)  # 关键词

    def __post_init__(self):
        if not self.word_count:
            self.word_count = len(self.content)


__all__ = [
    "ScriptStyle",
    "VoiceTone",
    "ScriptConfig",
    "ScriptSegment",
    "GeneratedScript",
]
