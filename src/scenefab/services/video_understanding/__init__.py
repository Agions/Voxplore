"""
SceneFab 多模态长时序视频理解模块

功能：
1. 长视频分段策略
2. 多模型协同理解（Qwen3.7-Flash + Qwen3.7-Max + Gemini 3.1 Pro）
3. 人物关系图谱构建
4. 剧情摘要生成
5. 关键事件时间戳定位

技术栈：
- Qwen3.7-Flash: 轻量实时帧理解（本地/API）
- Qwen3.7-Max: 复杂场景推理（API）
- Gemini 3.1 Pro: 长时序电影级理解（API，100万 token）
"""

from scenefab.services.video_understanding.core import (
    LongVideoUnderstanding,
    understand_long_video,
)
from scenefab.services.video_understanding.models import (
    Character,
    LongVideoUnderstandingResult,
    PlotEvent,
    StoryGraph,
    UnderstandingLevel,
    VideoSegment,
)

__all__ = [
    "Character",
    "LongVideoUnderstanding",
    "LongVideoUnderstandingResult",
    "PlotEvent",
    "StoryGraph",
    "UnderstandingLevel",
    "VideoSegment",
    "understand_long_video",
]
