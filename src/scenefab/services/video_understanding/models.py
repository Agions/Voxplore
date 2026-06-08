"""
SceneFab 长视频理解数据模型

包含视频片段、人物、事件、剧情图谱等数据结构定义。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class UnderstandingLevel(str, Enum):
    """理解级别"""
    FLASH = "flash"  # 快速理解（Qwen3.7-Flash）
    STANDARD = "standard"  # 标准理解（Qwen3.7-Max）
    DEEP = "deep"  # 深度理解（Gemini 3.1 Pro）


@dataclass
class VideoSegment:
    """视频片段"""
    segment_id: int
    start_time: float  # 开始时间（秒）
    end_time: float  # 结束时间（秒）
    duration: float  # 时长（秒）
    key_frames: list[dict[str, Any]] = field(default_factory=list)  # 关键帧
    summary: str = ""  # 片段摘要
    characters: list[str] = field(default_factory=list)  # 出现的人物
    emotions: list[str] = field(default_factory=list)  # 情绪标签
    events: list[dict[str, Any]] = field(default_factory=list)  # 事件列表


@dataclass
class Character:
    """人物信息"""
    character_id: str
    name: str
    description: str = ""
    appearances: list[dict[str, Any]] = field(default_factory=list)  # 出场记录
    relationships: dict[str, str] = field(default_factory=dict)  # 与其他人物的关系
    importance: float = 0.0  # 重要性 0.0-1.0


@dataclass
class PlotEvent:
    """剧情事件"""
    event_id: str
    timestamp: float  # 时间戳（秒）
    event_type: str  # event_type: "introduction", "development", "climax", "resolution"
    description: str
    characters_involved: list[str] = field(default_factory=list)
    importance: float = 0.0  # 重要性 0.0-1.0
    cause: str = ""  # 原因
    effect: str = ""  # 结果


@dataclass
class StoryGraph:
    """剧情图谱"""
    title: str = ""
    genre: str = ""  # 类型：action, drama, comedy, etc.
    synopsis: str = ""  # 剧情梗概
    characters: list[Character] = field(default_factory=list)
    plot_events: list[PlotEvent] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)  # 时间线
    themes: list[str] = field(default_factory=list)  # 主题
    emotional_arc: list[dict[str, Any]] = field(default_factory=list)  # 情绪弧线


@dataclass
class LongVideoUnderstandingResult:
    """长视频理解结果"""
    video_path: str
    video_duration: float  # 视频时长（秒）
    understanding_level: UnderstandingLevel
    segments: list[VideoSegment] = field(default_factory=list)
    story_graph: StoryGraph = field(default_factory=StoryGraph)
    processing_time: float = 0.0  # 处理时间（秒）
    token_usage: dict[str, int] = field(default_factory=dict)  # Token 使用量
    understanding_time: str = ""
    understander_version: str = "1.0.0"
