"""
视频工具服务

活跃模块：
- FFmpegTool        FFmpeg 封装（视频/音频处理便捷门面）
- hardware          硬件加速检测（HWAccelType + detect_hw_accel 等）
- probe             ffprobe 视频元数据探测
- CaptionGenerator  动态字幕生成
- BaseVideoProcessor / IVideoProcessor  视频处理基类
"""

from . import hardware, probe
from .base import (
    BaseVideoProcessor,
    IVideoProcessor,
    ProcessingResult,
    VideoMetadata,
)
from .caption_generator import Caption, CaptionConfig, CaptionGenerator, CaptionStyle
from .ffmpeg_tool import FFmpegTool, HWAccelType

__all__ = [
    # 工具
    "FFmpegTool",
    "HWAccelType",
    # 拆出的子模块
    "hardware",
    "probe",
    # 基类
    "IVideoProcessor",
    "BaseVideoProcessor",
    "VideoMetadata",
    "ProcessingResult",
    # 字幕生成
    "CaptionGenerator",
    "Caption",
    "CaptionConfig",
    "CaptionStyle",
]
