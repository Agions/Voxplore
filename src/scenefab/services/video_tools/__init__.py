"""
视频工具服务

活跃模块：
- FFmpegTool        FFmpeg 封装（视频/音频处理）
- CaptionGenerator  动态字幕生成
- BaseVideoProcessor / IVideoProcessor  视频处理基类
"""

from .ffmpeg_tool import FFmpegTool, HWAccelType
from .base import (
    IVideoProcessor,
    BaseVideoProcessor,
    VideoMetadata,
    ProcessingResult,
    get_seg_attr,
    parse_fps,
    extract_video_metadata,
)
from .caption_gen import CaptionGenerator, Caption, CaptionConfig, CaptionStyle

__all__ = [
    # 工具
    "FFmpegTool",
    "HWAccelType",

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
