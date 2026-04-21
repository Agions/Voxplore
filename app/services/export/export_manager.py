#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一导出管理器
提供一键导出到多种格式的能力
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import logging
from ...core.exceptions import ExportError
from .jianying_exporter import JianyingExporter
from .direct_video_exporter import DirectVideoExporter

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """导出格式"""
    JIANYING = "jianying"       # 剪映草稿
    MP4 = "mp4"                 # 直接导出 MP4
    MOV = "mov"                 # 直接导出 MOV
    GIF = "gif"                 # 导出 GIF


@dataclass
class ExportConfig:
    """导出配置"""
    format: ExportFormat = ExportFormat.MP4
    quality: str = "high"       # low/medium/high/ultra
    resolution: str = "1080p"   # 720p/1080p/4k
    fps: int = 30
    codec: str = "h264"         # h264/h265/vp9
    audio_codec: str = "aac"
    bitrate: str = "8M"
    output_path: Optional[str] = None
    progress_callback: Any = None

    # 特定格式配置
    jianying_version: str = "6.0"  # 剪映版本


class ExportManager:
    """统一导出管理器"""

    def __init__(self):
        self.exporters = {
            ExportFormat.JIANYING: JianyingExporter(),
            ExportFormat.MP4: DirectVideoExporter(),
            ExportFormat.MOV: DirectVideoExporter(),
            ExportFormat.GIF: DirectVideoExporter(),
        }

    def export(
        self,
        project_data: Dict[str, Any],
        config: ExportConfig
    ) -> bool:
        """
        导出项目

        Args:
            project_data: 项目数据
            config: 导出配置

        Returns:
            bool: 是否导出成功
        """
        exporter = self.exporters.get(config.format)
        if not exporter:
            raise ExportError(
                message=f"不支持的导出格式",
                format=config.format,
            )

        # 准备输出路径
        if not config.output_path:
            config.output_path = self._generate_output_path(config)

        # 执行导出
        try:
            return exporter.export(project_data, config)
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return False

    def _generate_output_path(self, config: ExportConfig) -> str:
        """生成输出路径"""
        output_dir = Path.home() / "Voxplore" / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)

        suffix = config.format.value
        if config.format in [ExportFormat.MP4, ExportFormat.MOV]:
            suffix = config.format.value

        import time
        return str(output_dir / f"export_{int(time.time())}.{suffix}")

    def get_supported_formats(self) -> List[ExportFormat]:
        """获取支持的导出格式"""
        return list(self.exporters.keys())

    def get_format_info(self, format_type: ExportFormat) -> Dict[str, Any]:
        """获取格式信息"""
        info = {
            ExportFormat.JIANYING: {
                "name": "剪映草稿",
                "description": "导出为剪映草稿，可在剪映中继续编辑",
                "platforms": ["iOS", "Android", "macOS", "Windows"],
            },
            ExportFormat.MP4: {
                "name": "MP4 视频",
                "description": "直接导出为 MP4 视频文件",
                "platforms": ["全平台"],
            },
            ExportFormat.MOV: {
                "name": "MOV 视频",
                "description": "直接导出为 MOV 视频文件",
                "platforms": ["全平台"],
            },
            ExportFormat.GIF: {
                "name": "GIF 动图",
                "description": "导出为 GIF 动图",
                "platforms": ["全平台"],
            },
        }
        return info.get(format_type, {})
