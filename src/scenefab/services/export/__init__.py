"""
SceneFab 导出服务模块

提供视频项目的导出能力:
- JianyingExporter: 剪映草稿导出
- DirectVideoExporter: MP4/MOV/GIF 视频文件导出
- BaseExporter: 导出器基类
"""

from .batch_export_manager import (
    BatchExportManager,
    BatchExportResult,
    ExportStatus,
    ExportTask,
    get_batch_export_manager,
)
from .direct_video_exporter import (
    DirectVideoExporter,
    HWAccel,
    Resolution,
    VideoCodec,
    VideoExportConfig,
    VideoFormat,
)
from .export_manager import ExportManager
from .export_utils import (
    BaseExporter,
    BaseMaterial,
    BaseProject,
    BaseSegment,
    BaseTrack,
    ExporterConfig,
    copy_material_to_folder,
    get_video_duration,
    get_video_resolution,
    safe_filename,
)
from .jianying_adapter import (
    AudioMaterial,
    CanvasConfig,
    JianyingConfig,
    JianyingDraft,
    JianyingMaterials,
    Segment,
    TextMaterial,
    TimeRange,
    Track,
    TrackType,
    VideoMaterial,
)
from .jianying_exporter import JianyingExporter
from .presets import ExportPreset
from .video_exporter import ExportConfig, ExportFormat, VideoExporter

__all__ = [
    # 基类
    "BaseExporter",
    "BaseProject",
    "BaseTrack",
    "BaseSegment",
    "BaseMaterial",
    "ExporterConfig",
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
    "ExportPreset",
    "BatchExportResult",
    "get_batch_export_manager",
    # 导出管理
    "ExportManager",
]
