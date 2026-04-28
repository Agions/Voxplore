"""
视频文件导出器 (Video Exporter)

将项目直接导出为视频文件。

使用示例:
    from app.services.export import VideoExporter, ExportConfig, ExportFormat

    exporter = VideoExporter()
    output = exporter.export(
        video_path="input.mp4",
        audio_path="voiceover.mp3",
        output_path="output.mp4",
    )
"""

import subprocess
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum
from ...core.exceptions import ExportError
from ..video_tools.ffmpeg_tool import FFmpegTool


class ExportFormat(Enum):
    """导出格式"""
    MP4 = "mp4"
    MOV = "mov"
    WEBM = "webm"
    GIF = "gif"


class VideoCodec(Enum):
    """视频编码器"""
    H264 = "libx264"
    H265 = "libx265"
    VP9 = "libvpx-vp9"
    PRORES = "prores_ks"


class AudioCodec(Enum):
    """音频编码器"""
    AAC = "aac"
    MP3 = "libmp3lame"
    OPUS = "libopus"


@dataclass
class ExportConfig:
    """导出配置"""
    # 格式
    format: ExportFormat = ExportFormat.MP4
    video_codec: VideoCodec = VideoCodec.H264
    audio_codec: AudioCodec = AudioCodec.AAC

    # 质量
    video_bitrate: str = "5M"      # 视频码率
    audio_bitrate: str = "192k"    # 音频码率
    crf: int = 23                  # 恒定质量因子 (0-51, 越低质量越好)
    preset: str = "medium"         # 编码预设

    # 分辨率
    width: int = 1080
    height: int = 1920
    fps: int = 30

    # 硬件加速
    use_hw_accel: bool = True
    hw_accel_type: str = "videotoolbox"  # videotoolbox (mac), nvenc, qsv


class VideoExporter:
    """
    视频文件导出器

    使用 FFmpeg 将项目导出为视频文件
    """

    def __init__(self, config: Optional[ExportConfig] = None):
        self.config = config or ExportConfig()
        FFmpegTool.check_ffmpeg()

    def export(
        self,
        video_path: str,
        audio_path: Optional[str] = None,
        output_path: str = "output.mp4",
        subtitles_path: Optional[str] = None,
    ) -> str:
        """
        导出视频

        Args:
            video_path: 源视频路径
            audio_path: 音频路径（替换原音轨）
            output_path: 输出路径
            subtitles_path: 字幕文件路径 (.ass/.srt)

        Returns:
            输出视频路径
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        cmd = ['ffmpeg', '-y']

        # 输入
        cmd.extend(['-i', video_path])

        if audio_path:
            cmd.extend(['-i', audio_path])

        # 滤镜
        filters = []

        # 缩放
        filters.append(f"scale={self.config.width}:{self.config.height}")

        # 字幕（如果有）
        if subtitles_path and Path(subtitles_path).exists():
            # 使用 ass 滤镜烧录字幕
            filters.append(f"ass={subtitles_path}")

        if filters:
            cmd.extend(['-vf', ','.join(filters)])

        # 视频编码
        if self.config.use_hw_accel:
            cmd.extend(self._get_hw_accel_params())
        else:
            cmd.extend(['-c:v', self.config.video_codec.value])
            cmd.extend(['-preset', self.config.preset])
            cmd.extend(['-crf', str(self.config.crf)])

        cmd.extend(['-b:v', self.config.video_bitrate])
        cmd.extend(['-r', str(self.config.fps)])

        # 音频编码
        cmd.extend(['-c:a', self.config.audio_codec.value])
        cmd.extend(['-b:a', self.config.audio_bitrate])

        # 映射
        cmd.extend(['-map', '0:v:0'])
        if audio_path:
            cmd.extend(['-map', '1:a:0'])
        else:
            cmd.extend(['-map', '0:a:0?'])

        # 其他
        cmd.extend(['-shortest'])
        cmd.extend(['-movflags', '+faststart'])

        # 输出
        cmd.append(str(output))

        # 执行
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ExportError(
                message="导出失败",
                details={"stderr": result.stderr, "cmd": " ".join(cmd)}
            )

        return str(output)

    def _get_hw_accel_params(self) -> List[str]:
        """获取硬件加速参数"""
        params = []

        if self.config.hw_accel_type == "videotoolbox":
            # macOS VideoToolbox
            params.extend(['-c:v', 'h264_videotoolbox'])
            params.extend(['-q:v', '60'])
        elif self.config.hw_accel_type == "nvenc":
            # NVIDIA NVENC
            params.extend(['-c:v', 'h264_nvenc'])
            params.extend(['-preset', 'p4'])
            params.extend(['-cq', str(self.config.crf)])
        elif self.config.hw_accel_type == "qsv":
            # Intel Quick Sync
            params.extend(['-c:v', 'h264_qsv'])
            params.extend(['-preset', 'medium'])
        else:
            # 无硬件加速
            params.extend(['-c:v', self.config.video_codec.value])
            params.extend(['-preset', self.config.preset])
            params.extend(['-crf', str(self.config.crf)])

        return params

    def concat_videos(
        self,
        video_paths: List[str],
        output_path: str,
    ) -> str:
        """
        拼接多个视频

        Args:
            video_paths: 视频路径列表
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件列表
        list_file = output.parent / "concat_list.txt"
        with open(list_file, 'w') as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")

        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file),
            '-c', 'copy',
            str(output)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # 清理
        list_file.unlink(missing_ok=True)

        if result.returncode != 0:
            raise ExportError(
                message="拼接失败",
                details={"stderr": result.stderr}
            )

        return str(output)

    def add_audio_to_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        mix_with_original: bool = False,
        audio_volume: float = 1.0,
        original_volume: float = 0.3,
    ) -> str:
        """
        为视频添加音频轨道

        Args:
            video_path: 视频路径
            audio_path: 音频路径
            output_path: 输出路径
            mix_with_original: 是否与原音轨混合
            audio_volume: 新音频音量
            original_volume: 原音频音量

        Returns:
            输出视频路径
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        cmd = ['ffmpeg', '-y', '-i', video_path, '-i', audio_path]

        if mix_with_original:
            # 混合音频
            cmd.extend([
                '-filter_complex',
                f"[0:a]volume={original_volume}[a0];"
                f"[1:a]volume={audio_volume}[a1];"
                f"[a0][a1]amix=inputs=2:duration=shortest[aout]",
                '-map', '0:v',
                '-map', '[aout]',
            ])
        else:
            # 替换音频
            cmd.extend([
                '-map', '0:v',
                '-map', '1:a',
            ])

        cmd.extend([
            '-c:v', 'copy',
            '-c:a', self.config.audio_codec.value,
            '-shortest',
            str(output)
        ])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ExportError(
                message="添加音频失败",
                details={"stderr": result.stderr}
            )

        return str(output)

    def create_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp: float = 1.0,
        width: int = 1280,
        height: int = 720,
    ) -> str:
        """
        创建视频缩略图

        Args:
            video_path: 视频路径
            output_path: 输出图片路径
            timestamp: 截取时间点（秒）
            width: 宽度
            height: 高度

        Returns:
            缩略图路径
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-vf', f'scale={width}:{height}',
            '-q:v', '2',
            str(output)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ExportError(
                message="创建缩略图失败",
                details={"stderr": result.stderr}
            )

        return str(output)


def demo_export():
    """演示视频导出"""
    import logging
    logger = logging.getLogger(__name__)

    exporter = VideoExporter(ExportConfig(
        width=1080,
        height=1920,
        use_hw_accel=True,
    ))

    logger.info("VideoExporter 已初始化")
    logger.info(f"  格式: {exporter.config.format.value}")
    logger.info(f"  分辨率: {exporter.config.width}x{exporter.config.height}")
    logger.info(f"  硬件加速: {exporter.config.use_hw_accel}")


if __name__ == '__main__':
    demo_export()
