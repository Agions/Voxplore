"""
视频导出器基类 (Base Exporter)

提供导出器的公共抽象:
- JianyingExporter: 剪映草稿导出
- PremiereExporter: Adobe Premiere 导出
- FinalCutExporter: Final Cut Pro 导出
- DaVinciExporter: DaVinci Resolve 导出
"""

import json
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Generic, TypeVar
from dataclasses import dataclass, field
import logging
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
    ticks_per_second = 254016000000  # Premiere tick rate
    return int(seconds * ticks_per_second)


def safe_filename(name: str) -> str:
    """生成安全的文件名"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


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
    start: float = 0.0      # 目标开始时间（秒）
    duration: float = 0.0   # 持续时间（秒）
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
    width: int = 1920
    height: int = 1080
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

    def __init__(self, config: Optional[C] = None):
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
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _get_output_path(self, output_dir: str, name: str, extension: str) -> Path:
        """获取输出文件路径"""
        return self._ensure_output_dir(output_dir) / f"{safe_filename(name)}.{extension}"

    def _write_json(self, path: Path, data: dict, indent: int = 2) -> None:
        """写入 JSON 文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)

    def _read_json(self, path: Path) -> dict:
        """读取 JSON 文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


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


# ========== 便捷类 ==========

class TimeHelper:
    """时间转换辅助类"""

    # Premiere tick rate
    TICKS_PER_SECOND = 254016000000

    @staticmethod
    def seconds_to_us(seconds: float) -> int:
        """秒转微秒"""
        return int(seconds * 1_000_000)

    @staticmethod
    def us_to_seconds(us: int) -> float:
        """微秒转秒"""
        return us / 1_000_000

    @staticmethod
    def seconds_to_ticks(seconds: float) -> int:
        """秒转 ticks"""
        return int(seconds * TimeHelper.TICKS_PER_SECOND)

    @staticmethod
    def ticks_to_seconds(ticks: int) -> float:
        """ticks 转秒"""
        return ticks / TimeHelper.TICKS_PER_SECOND

    @staticmethod
    def seconds_to_frames(seconds: float, fps: float) -> int:
        """秒转帧数"""
        return int(seconds * fps)

    @staticmethod
    def frames_to_seconds(frames: int, fps: float) -> float:
        """帧数转秒"""
        return frames / fps


__all__ = [
    # 工具函数
    "seconds_to_microseconds",
    "microseconds_to_seconds",
    "seconds_to_ticks",
    "safe_filename",
    "get_video_duration",
    "get_video_resolution",
    "copy_material_to_folder",
    "TimeHelper",

    # 基础类
    "BaseTrack",
    "BaseSegment",
    "BaseMaterial",
    "BaseProject",
    "ExporterConfig",
    "BaseExporter",
]
