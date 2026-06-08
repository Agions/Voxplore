"""
视频处理服务基类

提供视频处理服务的公共基类和接口
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    """视频元数据"""
    path: str
    duration: float = 0.0
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    bitrate: int = 0
    codec: str = ""
    size_bytes: int = 0


@dataclass
class ProcessingResult:
    """处理结果基类"""
    success: bool
    output_path: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# =========== 通用工具函数 ===========

def get_seg_attr(seg: dict | object, key: str, default: Any = None) -> Any:
    """
    从片段获取属性，兼容 dict 和对象两种格式

    Args:
        seg: 片段（可能是 dict 或带属性的对象）
        key: 属性名
        default: 默认值

    Returns:
        属性值或默认值
    """
    if isinstance(seg, dict):
        return seg.get(key, default)
    return getattr(seg, key, default)


def parse_fps(fps_str: str) -> float:
    """
    解析 FPS 字符串（如 '30000/1001'）为浮点数

    Args:
        fps_str: FPS 字符串

    Returns:
        FPS 浮点数值
    """
    if not fps_str or fps_str == '0/0':
        return 0.0
    if '/' in fps_str:
        num, den = fps_str.split('/')
        return float(num) / float(den) if float(den) != 0 else 0.0
    return float(fps_str)


def extract_video_metadata(info: dict[str, Any]) -> dict[str, Any]:
    """
    从 FFmpegTool.get_video_info() 结果中提取视频元数据

    Args:
        info: FFmpegTool.get_video_info() 返回的原始信息

    Returns:
        包含 width, height, duration, fps 的字典
    """
    video_stream = next(
        (s for s in info.get('streams', []) if s.get('codec_type') == 'video'),
        {}
    )
    format_info = info.get('format', {})

    duration = float(format_info.get('duration') or 0)
    width = video_stream.get('width', 0) or 0
    height = video_stream.get('height', 0) or 0
    fps = parse_fps(video_stream.get('r_frame_rate', '0/1'))

    return {
        'width': width,
        'height': height,
        'duration': duration,
        'fps': fps,
    }


class IVideoProcessor(ABC):
    """视频处理器接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """处理器名称"""
        pass

    @abstractmethod
    def analyze(self, video_path: str) -> VideoMetadata:
        """分析视频获取元数据"""
        pass

    @abstractmethod
    def process(self, video_path: str, **kwargs) -> ProcessingResult:
        """处理视频"""
        pass

    @abstractmethod
    def validate_input(self, video_path: str) -> bool:
        """验证输入视频"""
        pass


class BaseVideoProcessor(IVideoProcessor):
    """
    视频处理器基类

    提供公共的视频处理功能
    """

    def __init__(self):
        self._supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm']

    @property
    def supported_formats(self) -> list[str]:
        """支持的视频格式"""
        return self._supported_formats

    def validate_input(self, video_path: str) -> bool:
        """验证输入视频"""
        path = Path(video_path)

        if not path.exists():
            return False

        if path.suffix.lower() not in self._supported_formats:
            return False

        return True

    def analyze(self, video_path: str) -> VideoMetadata:
        """分析视频获取元数据"""
        from .ffmpeg_tool import FFmpegTool

        info = FFmpegTool.get_video_info(video_path)
        meta = extract_video_metadata(info)
        format_info = info.get('format', {})

        # 获取文件大小
        size_bytes = 0
        try:
            size_bytes = Path(video_path).stat().st_size
        except OSError as e:
            logger.debug(f"Failed to get file size for {video_path}: {e}")

        bitrate = int(format_info.get('bit_rate') or 0)

        return VideoMetadata(
            path=video_path,
            duration=meta['duration'],
            width=meta['width'],
            height=meta['height'],
            fps=meta['fps'],
            bitrate=bitrate,
            size_bytes=size_bytes,
        )

    def get_output_path(self, input_path: str, suffix: str = "_processed") -> str:
        """生成输出路径"""
        path = Path(input_path)
        stem = path.stem
        suffix_str = f"{suffix}{path.suffix}"
        return str(path.parent / f"{stem}{suffix_str}")
