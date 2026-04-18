"""
字幕数据类型定义

所有字幕相关模块共享的数据类，无循环依赖。
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SubtitleSegment:
    """字幕片段"""
    start: float           # 开始时间（秒）
    end: float             # 结束时间（秒）
    text: str              # 字幕文本
    confidence: float = 1.0
    source: str = ""       # "ocr" / "speech" / "merged"


@dataclass
class SubtitleExtractionResult:
    """字幕提取结果"""
    video_path: str
    duration: float
    segments: List[SubtitleSegment] = field(default_factory=list)
    full_text: str = ""
    language: str = "zh"
    method: str = ""       # "ocr" / "speech" / "both"
