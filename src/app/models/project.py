#!/usr/bin/env python3

"""
项目数据模型

包含视频项目、视频分组、任务进度等。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .media import AudioTrack, SubtitleItem
from .narration import EmotionType, NarrationBlock, NarrationStyle
from .video import EmotionPeak, VideoSegment


@dataclass
class VideoProject:
    """视频项目"""

    name: str
    source_videos: list[str] = field(default_factory=list)
    segments: list[VideoSegment] = field(default_factory=list)
    emotion_peaks: list[EmotionPeak] = field(default_factory=list)
    narration_blocks: list[NarrationBlock] = field(default_factory=list)
    subtitles: list[SubtitleItem] = field(default_factory=list)
    audio_track: AudioTrack | None = None
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

    def to_dict(self) -> dict[str, Any]:
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
            }
            if self.audio_track
            else None,
            "output_path": self.output_path,
            "style": self.style.value,
            "emotion": self.emotion.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class VideoGroup:
    """视频分组（用于多视频混剪）"""

    group_id: str
    name: str = ""
    video_paths: list[str] = field(default_factory=list)
    segments: list[VideoSegment] = field(default_factory=list)
    visual_similarity: float = 0.0
    audio_similarity: float = 0.0
    combined_similarity: float = 0.0

    def add_video(self, video_path: str):
        self.video_paths.append(video_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "video_paths": self.video_paths,
            "segments": [s.to_dict() for s in self.segments],
            "visual_similarity": self.visual_similarity,
            "audio_similarity": self.audio_similarity,
            "combined_similarity": self.combined_similarity,
        }


__all__ = ["VideoProject", "VideoGroup"]
