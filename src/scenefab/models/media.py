#!/usr/bin/env python3

"""
媒体数据模型

包含字幕项、音频轨道等。
"""

from dataclasses import dataclass


@dataclass(slots=True)
class SubtitleItem:
    """字幕项"""
    text: str
    start_time: float
    end_time: float
    confidence: float = 1.0

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_srt(self, index: int) -> str:
        """转换为 SRT 格式"""
        start = self._format_timestamp(self.start_time)
        end = self._format_timestamp(self.end_time)
        return f"{index}\n{start} --> {end}\n{self.text}\n"

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """格式化时间戳为 HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


@dataclass(slots=True)
class AudioTrack:
    """音频轨道"""
    audio_path: str
    duration: float
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: float = 1.0
    pitch: float = 0.0


__all__ = ["SubtitleItem", "AudioTrack"]