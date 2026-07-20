"""
视频导出器基类 (Base Exporter)

提供导出器的公共抽象:
- JianyingExporter: 剪映草稿导出
- PremiereExporter: Adobe Premiere 导出
- FinalCutExporter: Final Cut Pro 导出
- DaVinciExporter: DaVinci Resolve 导出
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, TypeVar

from scenefab.models.constants import (
    DEFAULT_VIDEO_HEIGHT,
    DEFAULT_VIDEO_WIDTH,
    PREMIERE_TICKS_PER_SECOND,
)

from ..video_tools.ffmpeg_tool import FFmpegTool

logger = logging.getLogger(__name__)


# ========== 时间处理工具 ==========


def seconds_to_microseconds(seconds: float) -> int:
    """秒转微秒"""
    return int(seconds * 1_000_000)


def microseconds_to_seconds(us: int) -> float:
    """微秒转秒"""
    return us / 1_000_000


def seconds_to_ticks(seconds: float, fps: float = 30.0) -> int:
    """秒转 ticks（Premiere/Final Cut 使用）"""
    return int(seconds * PREMIERE_TICKS_PER_SECOND)


def safe_filename(name: str) -> str:
    """生成安全的文件名"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, "_")
    return name.strip()


def ensure_directory(path: str | Path) -> Path:
    """确保目录存在并返回 Path。"""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_parent_directory(path: str | Path) -> Path:
    """确保文件路径的父目录存在并返回文件 Path。"""
    file_path = Path(path)
    ensure_directory(file_path.parent)
    return file_path


def write_json_file(path: str | Path, data: dict, indent: int = 2) -> None:
    """写入 UTF-8 JSON 文件。"""
    from ...utils.json_io import write_json

    write_json(path, data, indent=indent)


# ========== 基础数据模型 ==========


@dataclass
class BaseTrack:
    """轨道基类"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "video"  # video, audio, text


@dataclass
class BaseSegment:
    """片段基类"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    material_id: str = ""
    start: float = 0.0  # 目标开始时间（秒）
    duration: float = 0.0  # 持续时间（秒）
    source_start: float = 0.0  # 源开始时间


@dataclass
class BaseMaterial:
    """素材基类"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    duration: float = 0.0  # 秒


@dataclass
class BaseProject:
    """项目基类"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Project"
    duration: float = 0.0  # 总时长（秒）
    width: int = DEFAULT_VIDEO_WIDTH
    height: int = DEFAULT_VIDEO_HEIGHT
    fps: float = 30.0


# ========== 配置基类 ==========


@dataclass
class ExporterConfig:
    """导出配置基类"""

    copy_materials: bool = True
    output_dir: str = "."


# ========== 导出器基类 ==========

T = TypeVar("T", bound=BaseProject)
C = TypeVar("C", bound=ExporterConfig)


class BaseExporter(ABC, Generic[T, C]):
    """
    视频导出器基类

    提供公共功能:
    - 配置管理
    - 项目创建
    - 素材处理
    - 文件操作
    """

    def __init__(self, config: C | None = None):
        self.config = config

    @abstractmethod
    def create_project(self, name: str) -> T:
        """创建项目（子类实现）"""
        pass

    @abstractmethod
    def export(self, project: T, output_dir: str) -> str:
        """导出项目（子类实现）"""
        pass

    def _ensure_output_dir(self, output_dir: str) -> Path:
        """确保输出目录存在"""
        return ensure_directory(output_dir)

    def _get_output_path(self, output_dir: str, name: str, extension: str) -> Path:
        """获取输出文件路径"""
        return (
            self._ensure_output_dir(output_dir) / f"{safe_filename(name)}.{extension}"
        )

    def _write_json(self, path: Path, data: dict, indent: int = 2) -> None:
        """写入 JSON 文件"""
        write_json_file(path, data, indent=indent)


# ========== 便捷工具函数 ==========


def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    return FFmpegTool.get_duration(video_path)


def get_video_resolution(video_path: str) -> tuple:
    """获取视频分辨率 (width, height)"""
    return FFmpegTool.get_resolution(video_path)


def copy_material_to_folder(material_path: str, dest_folder: Path) -> str:
    """复制素材到目标文件夹，返回新路径"""
    import shutil

    src = Path(material_path)
    if not src.exists():
        return material_path

    dest_folder.mkdir(parents=True, exist_ok=True)
    dst = dest_folder / src.name

    if not dst.exists():
        shutil.copy2(src, dst)

    return str(dst)


__all__ = [
    # 工具函数
    "seconds_to_microseconds",
    "microseconds_to_seconds",
    "seconds_to_ticks",
    "safe_filename",
    "ensure_directory",
    "ensure_parent_directory",
    "write_json_file",
    "get_video_duration",
    "get_video_resolution",
    "copy_material_to_folder",
    # 基础类
    "BaseTrack",
    "BaseSegment",
    "BaseMaterial",
    "BaseProject",
    "ExporterConfig",
    "BaseExporter",
]
