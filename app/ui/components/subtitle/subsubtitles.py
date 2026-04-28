#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MultiTrack Subtitle System

多轨道字幕系统 - 提供专业的多轨道字幕编辑功能。

包含:
- SubtitleStylePreset: 字幕样式预设
- SubtitleBlock: 字幕块数据模型
- SubtitleTrack: 单条字幕轨道
- MultiTrackSubtitleEditor: 多轨道字幕编辑器
- SubtitleTrackWidget: 轨道编辑组件
- TimeRulerWidget: 时间标尺组件
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
import uuid


# ─────────────────────────────────────────────────────────────
# 字幕样式预设
# ─────────────────────────────────────────────────────────────

class SubtitlePosition(Enum):
    """字幕位置"""
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"
    CUSTOM = "custom"


class SubtitleAnimation(Enum):
    """字幕动画"""
    NONE = "none"
    FADE = "fade"
    TYPEWRITER = "typewriter"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM = "zoom"


@dataclass
class SubtitleStylePreset:
    """
    字幕样式预设

    定义字幕的外观和行为样式。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "默认样式"

    # 字体设置
    font_family: str = "思源黑体"
    font_size: float = 8.0          # 剪映相对尺寸
    font_weight: int = 400          # 字重
    font_color: str = "#FFFFFF"

    # 背景设置
    background_color: str = ""
    background_alpha: float = 0.0   # 0-1
    background_radius: float = 0.0  # 圆角

    # 描边/阴影
    stroke_color: str = ""
    stroke_width: float = 0.0
    shadow_color: str = ""
    shadow_offset_x: float = 0.0
    shadow_offset_y: float = 0.0
    shadow_blur: float = 0.0

    # 位置
    position: SubtitlePosition = SubtitlePosition.BOTTOM
    position_x_percent: float = 50.0  # X位置百分比
    position_y_percent: float = 85.0  # Y位置百分比
    alignment: int = 1                # 0=左, 1=中, 2=右

    # 动画
    animation: SubtitleAnimation = SubtitleAnimation.FADE
    animation_duration: float = 0.3   # 秒

    # 行间距
    line_spacing: float = 1.2

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "font_color": self.font_color,
            "background_color": self.background_color,
            "background_alpha": self.background_alpha,
            "background_radius": self.background_radius,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "shadow_color": self.shadow_color,
            "shadow_offset_x": self.shadow_offset_x,
            "shadow_offset_y": self.shadow_offset_y,
            "shadow_blur": self.shadow_blur,
            "position": self.position.value,
            "position_x_percent": self.position_x_percent,
            "position_y_percent": self.position_y_percent,
            "alignment": self.alignment,
            "animation": self.animation.value,
            "animation_duration": self.animation_duration,
            "line_spacing": self.line_spacing,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SubtitleStylePreset':
        """从字典创建"""
        data = dict(data)
        if "position" in data and isinstance(data["position"], str):
            data["position"] = SubtitlePosition(data["position"])
        if "animation" in data and isinstance(data["animation"], str):
            data["animation"] = SubtitleAnimation(data["animation"])
        return cls(**data)


# 预设样式
DEFAULT_PRESETS = {
    "cinematic": SubtitleStylePreset(
        name="电影感",
        font_size=8.0,
        font_color="#FFFFFF",
        position=SubtitlePosition.BOTTOM,
        animation=SubtitleAnimation.FADE,
        shadow_color="#000000",
        shadow_offset_x=1.0,
        shadow_offset_y=1.0,
        shadow_blur=3.0,
    ),
    "minimal": SubtitleStylePreset(
        name="简约",
        font_size=5.0,
        font_color="#E0E0E0",
        position=SubtitlePosition.BOTTOM,
        animation=SubtitleAnimation.NONE,
    ),
    "expressive": SubtitleStylePreset(
        name=" expressive",
        font_size=9.0,
        font_color="#FFFFFF",
        position=SubtitlePosition.CENTER,
        animation=SubtitleAnimation.TYPEWRITER,
        background_color="#000000",
        background_alpha=0.5,
        background_radius=4.0,
    ),
    " karaoke": SubtitleStylePreset(
        name="卡拉OK",
        font_size=8.0,
        font_color="#FFFFFF",
        position=SubtitlePosition.BOTTOM,
        animation=SubtitleAnimation.SLIDE_UP,
        stroke_color="#000000",
        stroke_width=1.0,
    ),
}


# ─────────────────────────────────────────────────────────────
# 字幕块
# ─────────────────────────────────────────────────────────────

@dataclass
class SubtitleBlock:
    """
    字幕块 - 单个字幕段落

    表示时间线上的一段字幕。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    track_id: str = ""

    # 内容
    text: str = ""

    # 时间（秒）
    start_time: float = 0.0
    end_time: float = 0.0

    # 样式
    style_id: str = ""

    # 元数据
    emphasis_words: List[str] = field(default_factory=list)  # 重音词
    translation: str = ""                                    # 翻译
    notes: str = ""                                          # 备注

    @property
    def duration(self) -> float:
        """持续时间"""
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "track_id": self.track_id,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "style_id": self.style_id,
            "emphasis_words": self.emphasis_words,
            "translation": self.translation,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SubtitleBlock':
        """从字典创建"""
        return cls(**data)

    def overlaps(self, other: 'SubtitleBlock') -> bool:
        """检测与另一个字幕块是否重叠"""
        return (self.start_time < other.end_time and
                self.end_time > other.start_time)


# ─────────────────────────────────────────────────────────────
# 字幕轨道
# ─────────────────────────────────────────────────────────────

@dataclass
class SubtitleTrack:
    """
    字幕轨道

    包含多个字幕块，属于同一轨道共享样式。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "字幕轨道"

    # 轨道设置
    enabled: bool = True
    locked: bool = False
    visible: bool = True

    # 样式预设ID
    style_id: str = "cinematic"

    # 字幕块列表
    blocks: List[SubtitleBlock] = field(default_factory=list)

    # 轨道颜色（用于UI显示）
    color: str = "#6366F1"

    def add_block(self, block: SubtitleBlock) -> None:
        """添加字幕块"""
        block.track_id = self.id
        self.blocks.append(block)

    def remove_block(self, block_id: str) -> bool:
        """移除字幕块"""
        for i, block in enumerate(self.blocks):
            if block.id == block_id:
                self.blocks.pop(i)
                return True
        return False

    def get_block_at(self, time: float) -> Optional[SubtitleBlock]:
        """获取指定时间的字幕块"""
        for block in self.blocks:
            if block.start_time <= time < block.end_time:
                return block
        return None

    def get_blocks_in_range(self, start: float, end: float) -> List[SubtitleBlock]:
        """获取指定时间范围内的字幕块"""
        result = []
        for block in self.blocks:
            if block.start_time < end and block.end_time > start:
                result.append(block)
        return result

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "locked": self.locked,
            "visible": self.visible,
            "style_id": self.style_id,
            "blocks": [b.to_dict() for b in self.blocks],
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SubtitleTrack':
        """从字典创建"""
        blocks_data = data.pop("blocks", [])
        track = cls(**data)
        track.blocks = [SubtitleBlock.from_dict(b) for b in blocks_data]
        for block in track.blocks:
            block.track_id = track.id
        return track


# ─────────────────────────────────────────────────────────────
# 多轨道字幕编辑器数据模型
# ─────────────────────────────────────────────────────────────

@dataclass
class MultiTrackSubtitleEditor:
    """
    多轨道字幕编辑器

    管理所有字幕轨道，提供统一的编辑接口。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "多轨道字幕编辑器"

    # 轨道列表
    tracks: List[SubtitleTrack] = field(default_factory=list)

    # 样式预设
    presets: Dict[str, SubtitleStylePreset] = field(default_factory=dict)

    # 项目设置
    duration: float = 0.0       # 总时长（秒）
    fps: float = 30.0

    # 当前状态
    current_track_id: Optional[str] = None
    current_time: float = 0.0

    def __post_init__(self):
        """初始化"""
        # 添加默认预设
        for preset_id, preset in DEFAULT_PRESETS.items():
            if preset_id not in self.presets:
                self.presets[preset_id] = preset

    # ─────────────────────────────────────────────────────────────
    # 轨道管理
    # ─────────────────────────────────────────────────────────────

    def add_track(self, track: SubtitleTrack) -> None:
        """添加轨道"""
        self.tracks.append(track)

    def remove_track(self, track_id: str) -> bool:
        """移除轨道"""
        for i, track in enumerate(self.tracks):
            if track.id == track_id:
                self.tracks.pop(i)
                return True
        return False

    def get_track(self, track_id: str) -> Optional[SubtitleTrack]:
        """获取轨道"""
        return next((t for t in self.tracks if t.id == track_id), None)

    def move_track(self, track_id: str, new_index: int) -> bool:
        """移动轨道位置"""
        for i, track in enumerate(self.tracks):
            if track.id == track_id:
                self.tracks.pop(i)
                self.tracks.insert(new_index, track)
                return True
        return False

    # ─────────────────────────────────────────────────────────────
    # 字幕块操作
    # ─────────────────────────────────────────────────────────────

    def add_block_to_track(self, track_id: str, block: SubtitleBlock) -> bool:
        """添加字幕块到轨道"""
        track = self.get_track(track_id)
        if track:
            track.add_block(block)
            return True
        return False

    def remove_block(self, block_id: str) -> bool:
        """移除字幕块"""
        for track in self.tracks:
            if track.remove_block(block_id):
                return True
        return False

    def get_block(self, block_id: str) -> Optional[SubtitleBlock]:
        """获取字幕块"""
        for track in self.tracks:
            for block in track.blocks:
                if block.id == block_id:
                    return block
        return None

    def get_all_blocks_at(self, time: float) -> List[SubtitleBlock]:
        """获取指定时间的所有轨道字幕块"""
        result = []
        for track in self.tracks:
            if track.enabled:
                block = track.get_block_at(time)
                if block:
                    result.append(block)
        return result

    # ─────────────────────────────────────────────────────────────
    # 样式预设
    # ─────────────────────────────────────────────────────────────

    def add_preset(self, preset: SubtitleStylePreset, preset_id: str = None) -> str:
        """添加样式预设"""
        if preset_id is None:
            preset_id = preset.id
        self.presets[preset_id] = preset
        return preset_id

    def get_preset(self, preset_id: str) -> Optional[SubtitleStylePreset]:
        """获取样式预设"""
        return self.presets.get(preset_id)

    def get_style_for_track(self, track: SubtitleTrack) -> SubtitleStylePreset:
        """获取轨道的样式"""
        return self.presets.get(track.style_id, DEFAULT_PRESETS["cinematic"])

    # ─────────────────────────────────────────────────────────────
    # 导出/序列化
    # ─────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "tracks": [t.to_dict() for t in self.tracks],
            "presets": {k: v.to_dict() for k, v in self.presets.items()},
            "duration": self.duration,
            "fps": self.fps,
            "current_track_id": self.current_track_id,
            "current_time": self.current_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MultiTrackSubtitleEditor':
        """从字典创建"""
        tracks_data = data.pop("tracks", [])
        presets_data = data.pop("presets", {})

        editor = cls(**data)

        # 恢复轨道
        for track_data in tracks_data:
            editor.tracks.append(SubtitleTrack.from_dict(track_data))

        # 恢复预设
        for preset_id, preset_data in presets_data.items():
            editor.presets[preset_id] = SubtitleStylePreset.from_dict(preset_data)

        return editor

    def calculate_duration(self) -> float:
        """计算总时长"""
        max_end = 0.0
        for track in self.tracks:
            for block in track.blocks:
                max_end = max(max_end, block.end_time)
        self.duration = max_end
        return max_end


# ─────────────────────────────────────────────────────────────
# 导出为剪映格式
# ─────────────────────────────────────────────────────────────

def export_to_jianying_text_track(
    editor: MultiTrackSubtitleEditor,
    track: SubtitleTrack,
) -> List[Dict]:
    """
    导出轨道为剪映字幕格式

    Args:
        editor: 字幕编辑器
        track: 字幕轨道

    Returns:
        剪映字幕段列表
    """
    style = editor.get_style_for_track(track)
    segments = []

    for block in sorted(track.blocks, key=lambda b: b.start_time):
        segments.append({
            "text": block.text,
            "start": block.start_time,
            "duration": block.duration,
            "style": style.to_dict(),
        })

    return segments


__all__ = [
    # 枚举
    "SubtitlePosition",
    "SubtitleAnimation",
    # 数据模型
    "SubtitleStylePreset",
    "SubtitleBlock",
    "SubtitleTrack",
    "MultiTrackSubtitleEditor",
    # 工具函数
    "DEFAULT_PRESETS",
    "export_to_jianying_text_track",
]
