#!/usr/bin/env python3

"""
项目管理器数据模型

定义项目相关的数据结构和枚举：
- ProjectStatus: 项目状态枚举
- ProjectType: 项目类型枚举
- ProjectMetadata: 项目元数据
- ProjectSettings: 项目设置
- ProjectMedia: 项目媒体文件
- ProjectTimeline: 项目时间线
- Project: 完整项目模型

使用示例:
    from scenefab.models.project_models import Project, ProjectType, ProjectMetadata
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


def _get_version() -> str:
    try:
        from scenefab import __version__

        return __version__
    except Exception:
        return "1.0.0"


class ProjectStatus(Enum):
    """项目状态枚举"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    TEMPLATE = "template"
    CORRUPTED = "corrupted"


class ProjectType(Enum):
    """项目类型枚举"""

    # ── 基础/业务层类型 ────────────────────────────────────────
    VIDEO_EDITING = ("video_editing", "视频剪辑", "基础视频剪辑模式")
    AI_ENHANCEMENT = ("ai_enhancement", "AI 增强", "AI 智能增强画质和音效")
    COMPILATION = ("compilation", "混剪合成", "多素材智能混剪")
    COMMENTARY = ("commentary", "AI 解说", "自动生成解说配音")
    STORY_ANALYSIS = ("story_analysis", "剧情分析", "AI 分析视频剧情并智能剪辑")
    MULTIMEDIA = ("multimedia", "多媒体", "综合多媒体项目")

    # ── 导出器/编排层类型 ────────────────────────────────────────
    RAW = ("raw", "原始项目", "未分类的原始项目")
    MASHUP = ("mashup", "视频混剪", "多素材混剪拼接")
    BEAT_SYNC = ("beat_sync", "Beat-sync 混剪", "按节拍同步的混剪")
    MONOLOGUE = ("monologue", "第一人称独白", "第一人称叙事独白视频")

    def __init__(self, value: str, display_name: str, description: str):
        self._value_ = value
        self.display_name = display_name
        self.description = description

    @property
    def value(self) -> str:
        return self._value_

    @classmethod
    def _missing_(cls, value: Any) -> Optional["ProjectType"]:
        """支持通过字符串 ID 查找枚举成员（如 ProjectType('ai_enhancement')）"""
        for member in cls:
            if member._value_ == value:
                return member
        return None


@dataclass
class ProjectMetadata:
    """项目元数据"""

    name: str = ""
    description: str = ""
    author: str = ""
    version: str = field(default_factory=_get_version)
    created_at: str = ""
    modified_at: str = ""
    tags: list[str] = field(default_factory=list)
    project_type: ProjectType = ProjectType.VIDEO_EDITING
    thumbnail: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    file_path: str = ""  # 项目文件路径

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["project_type"] = (
            self.project_type.value
            if isinstance(self.project_type, Enum)
            else self.project_type
        )
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMetadata":
        status_val = data.get("status", "active")
        if isinstance(status_val, str):
            status = ProjectStatus(status_val)
        else:
            status = status_val

        project_type_val = data.get("project_type", "video_editing")
        if isinstance(project_type_val, str):
            project_type = ProjectType(project_type_val)
        else:
            project_type = project_type_val

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0.1"),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            tags=data.get("tags", []),
            project_type=project_type,
            thumbnail=data.get("thumbnail", ""),
            status=status,
            file_path=data.get("file_path", ""),
        )


@dataclass
class ProjectSettings:
    """项目设置"""

    resolution: str = "1920x1080"
    fps: int = 30
    bitrate: str = "8000k"
    codec: str = "h264"
    audio_codec: str = "aac"
    sample_rate: int = 44100
    channels: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectSettings":
        return cls(
            resolution=data.get("resolution", "1920x1080"),
            fps=data.get("fps", 30),
            bitrate=data.get("bitrate", "8000k"),
            codec=data.get("codec", "h264"),
            audio_codec=data.get("audio_codec", "aac"),
            sample_rate=data.get("sample_rate", 44100),
            channels=data.get("channels", 2),
        )


@dataclass
class ProjectMedia:
    """项目媒体文件"""

    id: str = ""
    name: str = ""
    type: str = ""  # video, audio, image
    path: str = ""
    duration: float = 0.0  # 视频/音频时长（秒）
    size: int = 0  # 文件大小（字节）
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMedia":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            path=data.get("path", ""),
            duration=data.get("duration", 0.0),
            size=data.get("size", 0),
            width=data.get("width", 0),
            height=data.get("height", 0),
            fps=data.get("fps", 0.0),
            codec=data.get("codec", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class ProjectTimeline:
    """项目时间线"""

    tracks: list[dict[str, Any]] = field(default_factory=list)
    duration: float = 0.0  # 总时长（秒）
    in_point: float = 0.0
    out_point: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectTimeline":
        return cls(
            tracks=data.get("tracks", []),
            duration=data.get("duration", 0.0),
            in_point=data.get("in_point", 0.0),
            out_point=data.get("out_point", 0.0),
        )


__all__ = [
    "ProjectStatus",
    "ProjectType",
    "ProjectMetadata",
    "ProjectSettings",
    "ProjectMedia",
    "ProjectTimeline",
]
