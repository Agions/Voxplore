"""
视频导出共享工具与基础数据模型

提供各导出器（剪映草稿、直接视频导出等）共享的:
- 时间处理工具（seconds_to_microseconds）
- 文件名/目录工具（safe_filename/ensure_directory/ensure_parent_directory）
- JSON 写入（write_json_file）
- 视频信息工具（get_video_duration/get_video_resolution）
- 项目基础数据模型（BaseProject）
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from scenefab.models.constants import (
    DEFAULT_VIDEO_HEIGHT,
    DEFAULT_VIDEO_WIDTH,
)

from ..video.ffmpeg_tool import FFmpegTool

# ========== 时间处理工具 ==========


def seconds_to_microseconds(seconds: float) -> int:
    """秒转微秒"""
    return int(seconds * 1_000_000)


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
class BaseProject:
    """项目基类"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Project"
    duration: float = 0.0  # 总时长（秒）
    width: int = DEFAULT_VIDEO_WIDTH
    height: int = DEFAULT_VIDEO_HEIGHT
    fps: float = 30.0


# ========== 便捷工具函数 ==========


def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    return FFmpegTool.get_duration(video_path)


def get_video_resolution(video_path: str) -> tuple:
    """获取视频分辨率 (width, height)"""
    return FFmpegTool.get_resolution(video_path)


__all__ = [
    # 工具函数
    "seconds_to_microseconds",
    "safe_filename",
    "ensure_directory",
    "ensure_parent_directory",
    "write_json_file",
    "get_video_duration",
    "get_video_resolution",
    # 基础类
    "BaseProject",
]
