#!/usr/bin/env python3

"""
项目数据模型

包含视频项目、视频分组、任务进度等。

v2.5.0 新增 (Phase 2 · 多文件上传):
    - ``VideoSource``: 单个视频源元数据(路径/标签/时长/大小/缩略图)
    - ``MultiVideoSource``: 多视频源容器,统一入口,支持 4 种策略
    - ``SeriesContext``: 整季系列的共享上下文(剧情/角色/设定)
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from .media import AudioTrack, SubtitleItem
from .narration import EmotionType, NarrationBlock, NarrationStyle
from .video import EmotionPeak, VideoSegment

# ── 多视频上传策略 (ADR-001) ───────────────────────────────────────
MultiVideoStrategy = Literal["single", "concat", "batch", "series"]


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
    created_at: float = field(
        default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(
        default_factory=lambda: datetime.now().timestamp())

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


# ──────────────────────────────────────────────────────────────────
# v2.5.0 多文件上传扩展
# ──────────────────────────────────────────────────────────────────


@dataclass
class VideoSource:
    """单个视频源（带元数据/标签）。

    由 ``MultiVideoSource`` 持有，提供以下能力：
    - 顺序由 ``order`` 控制（拖拽区上下移动时改它）
    - ``label`` 可由用户重命名（默认 = 文件 stem）
    - ``duration`` / ``file_size`` 由探测（ffprobe / os.stat）回填
    """

    path: str
    label: str = ""
    duration: float = 0.0
    file_size: int = 0
    thumbnail: str | None = None
    order: int = 0

    def __post_init__(self) -> None:
        if not self.label:
            self.label = Path(self.path).stem

    @property
    def basename(self) -> str:
        return Path(self.path).name

    @property
    def exists(self) -> bool:
        return Path(self.path).is_file()


@dataclass
class SeriesContext:
    """整季系列的共享上下文。

    仅在 ``strategy == "series"`` 时启用。提供给 LLM 系统提示词，
    避免每集都重复设置人物/世界/情节走向。
    """

    series_title: str = ""
    episode_naming: str = "{title}_EP{ep:02d}"
    shared_characters: list[str] = field(default_factory=list)
    shared_plot: str = ""
    world_setting: str = ""
    genre: str = ""
    total_episodes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_title": self.series_title,
            "episode_naming": self.episode_naming,
            "shared_characters": list(self.shared_characters),
            "shared_plot": self.shared_plot,
            "world_setting": self.world_setting,
            "genre": self.genre,
            "total_episodes": self.total_episodes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SeriesContext":
        """从 ``to_dict()`` 生成的字典反序列化（v2.5.0）。

        容忍缺失字段 / 字段类型异常 — 允许对不完整字典安全降级。
        """
        # 非 dict 一律安全降级为默认实例（测试覆盖 ``None``/``""``/``42``）
        if not isinstance(data, dict):
            return cls()  # type: ignore[unreachable]
        try:
            return cls(
                series_title=str(data.get("series_title", "") or ""),
                episode_naming=str(
                    data.get("episode_naming", "") or "{title}_EP{ep:02d}"
                ),
                shared_characters=[
                    str(c) for c in data.get("shared_characters", []) or []
                ],
                shared_plot=str(data.get("shared_plot", "") or ""),
                world_setting=str(data.get("world_setting", "") or ""),
                genre=str(data.get("genre", "") or ""),
                total_episodes=int(data.get("total_episodes", 0) or 0),
            )
        except (TypeError, ValueError):
            return cls()


@dataclass
class MultiVideoSource:
    """多视频源统一入口。

    设计目标（ADR-001）：
    1. 单/多视频都通过这一个对象传入,消除 API 分叉
    2. 4 种策略由 ``strategy`` 字段决定（single/concat/batch/series）
    3. 顺序由 ``videos[*].order`` 决定,支持 add/remove/move/rename
    4. 旧调用方传单个 path 时,内部可转换为 ``MultiVideoSource([VideoSource(path)])``
    """

    videos: list[VideoSource] = field(default_factory=list)
    strategy: MultiVideoStrategy = "single"
    series_context: SeriesContext | None = None

    # ── 顺序操作 ──────────────────────────────────────────────────

    def add(
        self,
        path: str,
        *,
        label: str = "",
        duration: float = 0.0,
        file_size: int = 0,
    ) -> VideoSource:
        """追加一个视频（同 path 跳过；order 末尾）。

        返回: 新建或已存在的 ``VideoSource``（已存在时仍返回该对象，便于调用方获取元数据）。
        """
        for v in self.videos:
            if v.path == path:
                return v
        src = VideoSource(
            path=path,
            label=label,
            duration=duration,
            file_size=file_size,
            order=len(self.videos),
        )
        self.videos.append(src)
        return src

    def add_many(self, paths: Iterable[str]) -> int:
        """批量追加（去重）。返回实际新增数量。"""
        before = len(self.videos)
        for p in paths:
            self.add(p)
        return len(self.videos) - before

    def remove(self, index: int) -> VideoSource | None:
        """移除第 index 个视频,并重新编号 order。"""
        if not 0 <= index < len(self.videos):
            return None
        removed = self.videos.pop(index)
        for i, v in enumerate(self.videos):
            v.order = i
        return removed

    def move(self, src: int, dst: int) -> bool:
        """移动 src 到 dst（0-based）。同位置返回 False。"""
        if not 0 <= src < len(self.videos):
            return False
        if not 0 <= dst < len(self.videos):
            return False
        if src == dst:
            return False
        item = self.videos.pop(src)
        self.videos.insert(dst, item)
        for i, v in enumerate(self.videos):
            v.order = i
        return True

    def rename(self, index: int, new_label: str) -> bool:
        if not 0 <= index < len(self.videos):
            return False
        self.videos[index].label = new_label.strip()
        return True

    def clear(self) -> None:
        self.videos.clear()

    # ── 便捷属性 ──────────────────────────────────────────────────

    @property
    def paths(self) -> list[str]:
        """保持 order 顺序的所有 path。"""
        return [v.path for v in sorted(self.videos, key=lambda v: v.order)]

    @property
    def is_empty(self) -> bool:
        return len(self.videos) == 0

    @property
    def count(self) -> int:
        return len(self.videos)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "videos": [
                {
                    "path": v.path,
                    "label": v.label,
                    "duration": v.duration,
                    "file_size": v.file_size,
                    "thumbnail": v.thumbnail,
                    "order": v.order,
                }
                for v in sorted(self.videos, key=lambda v: v.order)
            ],
            "series_context": self.series_context.to_dict()
            if self.series_context
            else None,
        }


__all__ = [
    "VideoProject",
    "VideoGroup",
    # v2.5.0 多文件上传扩展
    "VideoSource",
    "MultiVideoSource",
    "SeriesContext",
    "MultiVideoStrategy",
]
