#!/usr/bin/env python3
"""
ExportPreset 数据模型 - 导出预设 (UI 兼容层)

历史背景:
- phase-2 重构 (commit 2bbdbf1) 删除了 scenefab.export.export_system 模块
- 多个 UI 组件 (export_panel / export_format_selector / export_progress)
  仍 import ExportPreset, 留下死引用导致 GUI 启动失败
- 本文件作为 shim 保留 API, 字段与原 dataclass 一致

正式数据流应使用 VideoExportConfig (direct_video_exporter) 或
JianyingConfig (jianying_adapter), 后续 v2.2 计划统一.
"""

import re
from dataclasses import dataclass
from typing import Any

DEFAULT_VERTICAL_RESOLUTION = "1080x1920"
DEFAULT_VIDEO_BITRATE_KBPS = 8000
DEFAULT_AUDIO_BITRATE_KBPS = 192

_RESOLUTION_PATTERN = re.compile(r"(?P<width>\d{2,5})\s*[xX×]\s*(?P<height>\d{2,5})")
_BITRATE_PATTERN = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mbps|m|kbps|k|bps)?\s*$",
    re.IGNORECASE,
)


def normalize_resolution(value: Any, default: str = DEFAULT_VERTICAL_RESOLUTION) -> str:
    """Return a canonical WIDTHxHEIGHT resolution string."""
    if hasattr(value, "width") and hasattr(value, "height"):
        try:
            return f"{int(value.width)}x{int(value.height)}"
        except (TypeError, ValueError):
            return default

    if isinstance(value, tuple | list) and len(value) >= 2:
        try:
            return f"{int(value[0])}x{int(value[1])}"
        except (TypeError, ValueError):
            return default

    match = _RESOLUTION_PATTERN.search(str(value))
    if not match:
        return default

    return f"{int(match.group('width'))}x{int(match.group('height'))}"


def parse_bitrate_kbps(value: Any, default: int = 0) -> int:
    """Parse bitrate values such as 8M, 8000k, 8000 kbps, or 192."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))

    match = _BITRATE_PATTERN.match(str(value))
    if not match:
        return default

    amount = float(match.group("value"))
    unit = (match.group("unit") or "kbps").lower()
    if unit in {"m", "mbps"}:
        amount *= 1000
    elif unit == "bps":
        amount /= 1000

    return max(1, int(round(amount)))


def normalize_bitrate(value: Any, default_kbps: int) -> str:
    """Return an ffmpeg-friendly bitrate string in kilobits per second."""
    return f"{parse_bitrate_kbps(value, default_kbps)}k"


def bitrate_label(value: Any, default_kbps: int = 0) -> str:
    """Return a compact human-readable bitrate label."""
    kbps = parse_bitrate_kbps(value, default_kbps)
    if kbps >= 1000 and kbps % 1000 == 0:
        return f"{kbps // 1000} Mbps"
    return f"{kbps} kbps"


@dataclass
class ExportPreset:
    """导出预设配置 (UI 兼容层)

    字段定义依据 (audit 2026-06-09):
    - export_panel.py:346 实例化: name/format/codec/resolution/fps/bitrate/
      audio_codec/audio_bitrate
    - bitrate/audio_bitrate 用字符串 ('8M' / '192k') 与 UI 控件 spinbox.value()
      转字符串保持一致
    - description / codec_params 预留, 供 export_format_selector 高级选项用
    """

    name: str = "新预设"
    format: str = "mp4"
    codec: str = "h264"
    resolution: str = DEFAULT_VERTICAL_RESOLUTION
    fps: int = 30
    bitrate: str = "8000k"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"  # UI 传 '192k' 字符串
    description: str = ""
    codec_params: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        self.resolution = normalize_resolution(self.resolution)
        self.fps = int(self.fps)
        self.bitrate = normalize_bitrate(self.bitrate, DEFAULT_VIDEO_BITRATE_KBPS)
        self.audio_bitrate = normalize_bitrate(
            self.audio_bitrate, DEFAULT_AUDIO_BITRATE_KBPS
        )
        if not self.id:
            self.id = self.name

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExportPreset":
        """从 dict 创建 (供 UI 对话框回填用)"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict"""
        return {
            "name": self.name,
            "format": self.format,
            "codec": self.codec,
            "resolution": self.resolution,
            "fps": self.fps,
            "bitrate": self.bitrate,
            "audio_codec": self.audio_codec,
            "audio_bitrate": self.audio_bitrate,
            "description": self.description,
            "codec_params": self.codec_params,
            "id": self.id,
        }


__all__ = [
    "DEFAULT_AUDIO_BITRATE_KBPS",
    "DEFAULT_VERTICAL_RESOLUTION",
    "DEFAULT_VIDEO_BITRATE_KBPS",
    "ExportPreset",
    "bitrate_label",
    "normalize_bitrate",
    "normalize_resolution",
    "parse_bitrate_kbps",
]
