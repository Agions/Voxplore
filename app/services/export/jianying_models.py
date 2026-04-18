#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
剪映草稿数据模型
JianyingDraft data models — dataclass based

包含:
- TrackType, MaterialType (枚举)
- TimeRange, Segment, Track (轨道模型)
- VideoMaterial, AudioMaterial, TextMaterial (素材模型)
- JianyingMaterials, CanvasConfig, JianyingDraft (复合模型)
- JianyingConfig (导出配置)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
import uuid
from datetime import datetime


# ─── 枚举定义 ────────────────────────────────────────────────

class TrackType(Enum):
    """轨道类型"""
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    STICKER = "sticker"
    EFFECT = "effect"


class MaterialType(Enum):
    """素材类型"""
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    IMAGE = "photo"
    SOUND_CHANNEL = "sound_channel"


# ─── 轨道模型 ────────────────────────────────────────────────

@dataclass
class TimeRange:
    """
    时间范围（剪映使用微秒）

    Attributes:
        start: 开始时间（微秒）
        duration: 持续时间（微秒）
    """
    start: int = 0
    duration: int = 0

    @classmethod
    def from_seconds(cls, start: float, duration: float) -> 'TimeRange':
        """从秒转换"""
        return cls(
            start=int(start * 1_000_000),
            duration=int(duration * 1_000_000)
        )

    def to_dict(self) -> dict:
        return {"start": self.start, "duration": self.duration}


@dataclass
class Segment:
    """
    片段模型

    对应剪映中的一个视频/音频/字幕片段
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    material_id: str = ""
    target_timerange: TimeRange = field(default_factory=TimeRange)
    source_timerange: TimeRange = field(default_factory=TimeRange)

    # 视频/音频属性
    volume: float = 1.0
    speed: float = 1.0

    # 字幕专用
    caption_info: Optional[Dict] = None

    def to_dict(self) -> dict:
        """转换为剪映 JSON 格式"""
        result = {
            "id": self.id,
            "material_id": self.material_id,
            "target_timerange": self.target_timerange.to_dict(),
            "source_timerange": self.source_timerange.to_dict(),
            "volume": self.volume,
            "speed": self.speed,
        }

        if self.caption_info:
            result["caption_info"] = self.caption_info

        return result


@dataclass
class Track:
    """
    轨道模型

    一个轨道可以包含多个片段
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: TrackType = TrackType.VIDEO
    segments: List[Segment] = field(default_factory=list)

    # 轨道属性
    attribute: int = 0  # 0=普通, 1=主轨道
    flag: int = 0

    def add_segment(self, segment: Segment) -> None:
        """添加片段"""
        self.segments.append(segment)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "segments": [s.to_dict() for s in self.segments],
            "attribute": self.attribute,
            "flag": self.flag,
        }


# ─── 素材模型 ────────────────────────────────────────────────

@dataclass
class VideoMaterial:
    """视频素材"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    duration: int = 0  # 微秒
    width: int = 1920
    height: int = 1080

    # 素材来源
    type: str = "video"
    category_id: str = ""
    category_name: str = "local"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "type": self.type,
            "category_id": self.category_id,
            "category_name": self.category_name,
        }


@dataclass
class AudioMaterial:
    """音频素材"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    duration: int = 0  # 微秒

    # 音频属性
    type: str = "music"
    name: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "duration": self.duration,
            "type": self.type,
            "name": self.name,
        }


@dataclass
class TextMaterial:
    """
    字幕/文本素材

    剪映字幕的核心结构
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""

    # 样式
    font_path: str = ""
    font_size: float = 8.0  # 剪映使用相对尺寸
    font_color: str = "#FFFFFF"

    # 位置
    alignment: int = 1  # 0=左, 1=中, 2=右

    # 特效
    background_color: str = ""
    has_shadow: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "font_path": self.font_path,
            "font_size": self.font_size,
            "font_color": self.font_color,
            "alignment": self.alignment,
            "background_color": self.background_color,
            "has_shadow": self.has_shadow,
            "type": "text",
        }


@dataclass
class JianyingMaterials:
    """素材集合"""
    videos: List[VideoMaterial] = field(default_factory=list)
    audios: List[AudioMaterial] = field(default_factory=list)
    texts: List[TextMaterial] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "videos": [v.to_dict() for v in self.videos],
            "audios": [a.to_dict() for a in self.audios],
            "texts": [t.to_dict() for t in self.texts],
        }


@dataclass
class CanvasConfig:
    """画布配置"""
    width: int = 1080  # 竖屏短视频
    height: int = 1920
    ratio: str = "9:16"

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "ratio": self.ratio,
        }


# ─── 复合模型 ────────────────────────────────────────────────

@dataclass
class JianyingDraft:
    """
    剪映草稿完整模型

    这是导出的核心数据结构，包含所有轨道、素材和配置信息
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Voxplore Project"
    duration: int = 0  # 总时长（微秒）

    # 轨道
    tracks: List[Track] = field(default_factory=list)

    # 素材
    materials: JianyingMaterials = field(default_factory=JianyingMaterials)

    # 配置
    canvas_config: CanvasConfig = field(default_factory=CanvasConfig)

    # 元数据
    create_time: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    update_time: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))

    # 版本
    version: int = 360000  # 剪映版本号
    platform: str = "all"

    def add_track(self, track: Track) -> None:
        """添加轨道"""
        self.tracks.append(track)

    def add_video(self, material: VideoMaterial) -> None:
        """添加视频素材"""
        self.materials.videos.append(material)

    def add_audio(self, material: AudioMaterial) -> None:
        """添加音频素材"""
        self.materials.audios.append(material)

    def add_text(self, material: TextMaterial) -> None:
        """添加文本素材"""
        self.materials.texts.append(material)

    def calculate_duration(self) -> None:
        """计算总时长"""
        max_end = 0
        for track in self.tracks:
            for segment in track.segments:
                end = segment.target_timerange.start + segment.target_timerange.duration
                max_end = max(max_end, end)
        self.duration = max_end

    def to_draft_content(self) -> dict:
        """
        生成 draft_content.json 内容

        这是剪映草稿的核心文件
        """
        self.calculate_duration()

        return {
            "id": self.id,
            "name": self.name,
            "duration": self.duration,
            "canvas_config": self.canvas_config.to_dict(),
            "tracks": [t.to_dict() for t in self.tracks],
            "materials": self.materials.to_dict(),
            "version": self.version,
            "platform": self.platform,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }

    def to_draft_meta_info(self) -> dict:
        """生成 draft_meta_info.json 内容"""
        return {
            "draft_id": self.id,
            "draft_name": self.name,
            "draft_root_path": "",  # 导出时填充
            "tm_draft_create": self.create_time // 1000,
            "tm_draft_modified": self.update_time // 1000,
            "draft_materials_copied": True,
        }


# ─── 导出配置 ────────────────────────────────────────────────

@dataclass
class JianyingConfig:
    """导出配置"""
    copy_materials: bool = True  # 是否复制素材到草稿目录
    canvas_ratio: str = "9:16"   # 画布比例: 9:16, 16:9, 1:1
    version: int = 360000        # 剪映版本号


__all__ = [
    # 枚举
    "TrackType",
    "MaterialType",
    # 轨道模型
    "TimeRange",
    "Segment",
    "Track",
    # 素材模型
    "VideoMaterial",
    "AudioMaterial",
    "TextMaterial",
    "JianyingMaterials",
    "CanvasConfig",
    # 复合模型
    "JianyingDraft",
    # 配置
    "JianyingConfig",
]
