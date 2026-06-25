#!/usr/bin/env python3

"""
统一导出管理器
提供一键导出到多种格式的能力
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from scenefab.exceptions import ExportError

from .direct_video_exporter import DirectVideoExporter
from .jianying_exporter import JianyingExporter

logger = logging.getLogger(__name__)

__all__ = [
    "ExportFormat",
    "ExportConfig",
    "ExportManager",
]


class ExportFormat(Enum):
    """导出格式"""

    JIANYING = "jianying"  # 剪映草稿
    MP4 = "mp4"  # 直接导出 MP4
    MOV = "mov"  # 直接导出 MOV
    GIF = "gif"  # 导出 GIF


@dataclass
class ExportConfig:
    """导出配置"""

    format: ExportFormat = ExportFormat.MP4
    quality: str = "high"  # low/medium/high/ultra
    resolution: str = "1080p"  # 720p/1080p/4k
    fps: int = 30
    codec: str = "h264"  # h264/h265/vp9
    audio_codec: str = "aac"
    bitrate: str = "8M"
    output_path: str | None = None
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
        self._last_error: str | None = None

    def export(self, project_data: dict[str, Any], config: ExportConfig) -> bool:
        """
        导出项目 (统一入口, 按 config.format 分发到具体 exporter)

        Args:
            project_data: 项目数据 (含 project_id, segments 等)
            config: 导出配置

        Returns:
            bool: 是否导出成功
        """
        exporter = self.exporters.get(config.format)
        if not exporter:
            raise ExportError(
                message="不支持的导出格式",
                format=config.format,  # type: ignore[arg-type]
            )

        # 准备输出路径
        if not config.output_path:
            config.output_path = self._generate_output_path(config)

        # 执行导出 — 不同 exporter 的统一入口签名不同, 显式 dispatch
        try:
            return self._dispatch(exporter, project_data, config)
        except ExportError:
            raise  # 已是对应异常，直接重新抛出
        except Exception as e:
            logger.error(f"导出失败: {e}")
            self._last_error = str(e)
            raise ExportError(f"导出失败: {e}")

    @staticmethod
    def _dispatch(
        exporter: Any, project_data: dict[str, Any], config: ExportConfig
    ) -> bool:
        """
        把 (project_data, config) 分发到正确的 exporter 方法.

        - JianyingExporter.export(draft, output_dir, progress_callback)
        - DirectVideoExporter.export(project_data, config)  (统一入口, 见下面 export 方法)

        Raises:
            ExportError: dict 缺少必填字段时给出明确错误 (不再 AttributeError)
        """
        if isinstance(exporter, JianyingExporter):
            if not isinstance(project_data, dict) or "draft" not in project_data:
                raise ExportError(
                    message="JianyingExporter 需要 project_data['draft'] = JianyingDraft 对象",
                    format=str(config.format.value),
                )
            output_dir = (
                str(Path(config.output_path).parent)
                if config.output_path
                else ""
            )
            result_path = exporter.export(
                draft=project_data["draft"],
                output_dir=output_dir,
                progress_callback=config.progress_callback,
            )
            config.output_path = result_path
            return True

        if isinstance(exporter, DirectVideoExporter):
            # DirectVideoExporter 已有统一 export 入口 (接受 project_data dict + config)
            if not config.output_path:
                raise ExportError(
                    message="DirectVideoExporter 需要 config.output_path",
                    format=str(config.format.value),
                )
            # 委托给 DirectVideoExporter.export, 它内部做格式分发
            return exporter.export(project_data, config)  # type: ignore[arg-type]

        raise ExportError(message="exporter 类型未知, 无法 dispatch", format=str(config.format.value))

    def _generate_output_path(self, config: ExportConfig) -> str:
        """生成输出路径"""
        output_dir = Path.home() / "SceneFab" / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)

        suffix = config.format.value
        if config.format in [ExportFormat.MP4, ExportFormat.MOV]:
            suffix = config.format.value

        import time

        return str(output_dir / f"export_{int(time.time())}.{suffix}")

    def get_supported_formats(self) -> list[ExportFormat]:
        """获取支持的导出格式"""
        return list(self.exporters.keys())

    def get_format_info(self, format_type: ExportFormat) -> dict[str, Any]:
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
