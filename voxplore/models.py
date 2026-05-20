#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 数据模型
定义核心业务对象
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


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
class TimeRange:
    """时间范围"""
    start: float  # 秒
    end: float    # 秒
    
    @property
    def duration(self) -> float:
        return self.end - self.start
    
    def to_dict(self) -> Dict[str, float]:
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
    
    def to_dict(self) -> Dict[str, Any]:
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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment": self.segment.to_dict(),
            "peak_score": self.peak_score,
            "reason": self.reason,
            "visual_score": self.visual_score,
            "audio_score": self.audio_score,
        }


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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "emotion": self.emotion.value,
            "style": self.style.value,
        }


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


# VideoProject 和 VideoGroup 使用 field(default_factory=list) 不支持 slots=True


@dataclass
class VideoProject:
    """视频项目"""
    name: str
    source_videos: List[str] = field(default_factory=list)
    segments: List[VideoSegment] = field(default_factory=list)
    emotion_peaks: List[EmotionPeak] = field(default_factory=list)
    narration_blocks: List[NarrationBlock] = field(default_factory=list)
    subtitles: List[SubtitleItem] = field(default_factory=list)
    audio_track: Optional[AudioTrack] = None
    output_path: str = ""
    style: NarrationStyle = NarrationStyle.DOCUMENTARY
    emotion: EmotionType = EmotionType.NEUTRAL
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def add_segment(self, segment: VideoSegment):
        self.segments.append(segment)
        self.updated_at = datetime.now().timestamp()
    
    def add_narration(self, narration: NarrationBlock):
        self.narration_blocks.append(narration)
        self.updated_at = datetime.now().timestamp()
    
    def set_audio(self, audio: AudioTrack):
        self.audio_track = audio
        self.updated_at = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_videos": self.source_videos,
            "segments": [s.to_dict() for s in self.segments],
            "emotion_peaks": [e.to_dict() for e in self.emotion_peaks],
            "narration_blocks": [n.to_dict() for n in self.narration_blocks],
            "subtitles": [
                {"text": s.text, "start": s.start_time, "end": s.end_time}
                for s in self.subtitles
            ],
            "audio_track": {
                "audio_path": self.audio_track.audio_path,
                "duration": self.audio_track.duration,
                "voice": self.audio_track.voice,
            } if self.audio_track else None,
            "output_path": self.output_path,
            "style": self.style.value,
            "emotion": self.emotion.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class TaskProgress:
    """任务进度"""
    task_id: str
    task_name: str
    status: str  # pending, running, paused, completed, failed, cancelled
    progress: float  # 0.0 - 1.0
    current_step: str = ""
    steps_total: int = 0
    steps_completed: int = 0
    message: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    
    @property
    def progress_percent(self) -> int:
        return int(self.progress * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status,
            "progress": self.progress,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "steps_total": self.steps_total,
            "steps_completed": self.steps_completed,
            "message": self.message,
            "error": self.error,
        }


@dataclass
class VideoGroup:
    """视频分组（用于多视频混剪）"""
    group_id: str
    name: str = ""
    video_paths: List[str] = field(default_factory=list)
    segments: List[VideoSegment] = field(default_factory=list)
    visual_similarity: float = 0.0
    audio_similarity: float = 0.0
    combined_similarity: float = 0.0
    
    def add_video(self, video_path: str):
        self.video_paths.append(video_path)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "video_paths": self.video_paths,
            "segments": [s.to_dict() for s in self.segments],
            "visual_similarity": self.visual_similarity,
            "audio_similarity": self.audio_similarity,
            "combined_similarity": self.combined_similarity,
        }


__all__ = [
    "NarrationStyle",
    "EmotionType",
    "TimeRange",
    "VideoSegment",
    "EmotionPeak",
    "NarrationBlock",
    "SubtitleItem",
    "AudioTrack",
    "VideoProject",
    "TaskProgress",
    "VideoGroup",
]
