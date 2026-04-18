"""
Voxplore 导出服务模块

提供视频项目的导出能力:
- JianyingExporter: 剪映草稿导出
- DirectVideoExporter: MP4/MOV/GIF 视频文件导出
- BaseExporter: 导出器基类
"""

from .base_exporter import (
    BaseExporter, BaseProject, BaseTrack, BaseSegment, BaseMaterial,
    ExporterConfig, TimeHelper, safe_filename,
    get_video_duration, get_video_resolution, copy_material_to_folder,
)
from .jianying_exporter import JianyingExporter
from .jianying_models import (
    JianyingDraft, JianyingConfig,
    Track, TrackType, Segment, TimeRange,
    VideoMaterial, AudioMaterial, TextMaterial,
    JianyingMaterials, CanvasConfig,
)
from .video_exporter import VideoExporter, ExportConfig, ExportFormat
from .direct_video_exporter import DirectVideoExporter, VideoExportConfig, Resolution, VideoCodec, VideoFormat, HWAccel
from .batch_export_manager import BatchExportManager, ExportTask, ExportStatus, BatchExportResult, get_batch_export_manager
from .export_manager import ExportManager


__all__ = [
    # 基类
    "BaseExporter",
    "BaseProject",
    "BaseTrack",
    "BaseSegment",
    "BaseMaterial",
    "ExporterConfig",
    "TimeHelper",
    "safe_filename",
    "get_video_duration",
    "get_video_resolution",
    "copy_material_to_folder",

    # 剪映草稿导出
    "JianyingExporter",
    "JianyingDraft",
    "JianyingConfig",
    "Track",
    "TrackType",
    "Segment",
    "TimeRange",
    "VideoMaterial",
    "AudioMaterial",
    "TextMaterial",
    "JianyingMaterials",
    "CanvasConfig",

    # 视频文件导出
    "VideoExporter",
    "ExportConfig",
    "ExportFormat",

    # 直接视频导出
    "DirectVideoExporter",
    "VideoExportConfig",
    "Resolution",
    "VideoCodec",
    "VideoFormat",
    "HWAccel",

    # 批量导出
    "BatchExportManager",
    "ExportTask",
    "ExportStatus",
    "BatchExportResult",
    "get_batch_export_manager",

    # 导出管理
    "ExportManager",
]
