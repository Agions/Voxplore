#!/usr/bin/env python3
"""
ExportPreset 数据模型 — 导出预设 (UI 兼容层)

历史背景:
- phase-2 重构 (commit 2bbdbf1) 删除了 scenefab.export.export_system 模块
- 多个 UI 组件 (export_panel / export_format_selector / export_progress)
  仍 import ExportPreset, 留下死引用导致 GUI 启动失败
- 本文件作为 shim 保留 API, 字段与原 dataclass 一致

正式数据流应使用 VideoExportConfig (direct_video_exporter) 或
JianyingConfig (jianying_adapter), 后续 v2.2 计划统一.
"""

from dataclasses import dataclass
from typing import Any


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
    resolution: str = "1920x1080"
    fps: int = 30
    bitrate: str = "8M"  # UI 传 '8M' / '5000k' 字符串, 与 from_dict 一致
    audio_codec: str = "aac"  # 修复 ② 缺失字段 — export_panel:347 用
    audio_bitrate: str = "192k"  # UI 传 '192k' 字符串
    description: str = ""
    codec_params: str = ""

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
        }


__all__ = ["ExportPreset"]
