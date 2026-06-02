#!/usr/bin/env python3

"""
视频数据模型

包含时间范围、视频片段、情感峰值等。
"""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TimeRange:
    """时间范围"""
    start: float  # 秒
    end: float    # 秒

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict[str, float]:
        return {"start": self.start, "end": self.end}

    @classmethod
    def from_seconds(cls, start: float, end: float) -> 'TimeRange':
        return cls(start=start, end=end)


@dataclass(slots=True)
class VideoSegment:
    """视频片段"""
    video_path: str
    start_time: float
    end_time: float
    confidence: float = 0.0
    description: str = ""
    group_id: str = ""

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def time_range(self) -> TimeRange:
        return TimeRange(self.start_time, self.end_time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_path": self.video_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "confidence": self.confidence,
            "description": self.description,
            "group_id": self.group_id,
        }


@dataclass(slots=True)
class EmotionPeak:
    """情感峰值"""
    segment: VideoSegment
    peak_score: float
    reason: str
    visual_score: float = 0.0
    audio_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment": self.segment.to_dict(),
            "peak_score": self.peak_score,
            "reason": self.reason,
            "visual_score": self.visual_score,
            "audio_score": self.audio_score,
        }


__all__ = ["TimeRange", "VideoSegment", "EmotionPeak"]