"""
视频处理服务基类

提供视频处理服务的公共基类和接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path
import logging
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
    metadata: Dict[str, Any] = field(default_factory=dict)


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
    def supported_formats(self) -> List[str]:
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
        video_stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), {})
        format_info = info.get('format', {})
        duration = float(format_info.get('duration') or 0)
        width = video_stream.get('width', 0) or 0
        height = video_stream.get('height', 0) or 0
        fps_str = video_stream.get('r_frame_rate', '0/1')
        num, denom = fps_str.split('/')
        fps = float(num) / float(denom) if float(denom) != 0 else 0.0

        # 获取文件大小
        size_bytes = 0
        try:
            size_bytes = Path(video_path).stat().st_size
        except OSError as e:
            logger.debug(f"Failed to get file size for {video_path}: {e}")

        bitrate = int(format_info.get('bit_rate') or 0)

        return VideoMetadata(
            path=video_path,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            bitrate=bitrate,
            size_bytes=size_bytes,
        )

    def get_output_path(self, input_path: str, suffix: str = "_processed") -> str:
        """生成输出路径"""
        path = Path(input_path)
        stem = path.stem
        suffix_str = f"{suffix}{path.suffix}"
        return str(path.parent / f"{stem}{suffix_str}")
