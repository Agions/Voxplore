"""
视频文件导出器 (Video Exporter)

将项目直接导出为视频文件。

使用示例:
    from scenefab.services.export import VideoExporter, ExportConfig, ExportFormat

    exporter = VideoExporter()
    output = exporter.export(
        video_path="input.mp4",
        audio_path="voiceover.mp3",
        output_path="output.mp4",
    )
"""

import warnings
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from scenefab.exceptions import ExportError
from scenefab.models.constants import DEFAULT_VIDEO_HEIGHT, DEFAULT_VIDEO_WIDTH

from ...utils.security import get_ffmpeg_executor


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
    video_bitrate: str = "5M"  # 视频码率
    audio_bitrate: str = "192k"  # 音频码率
    crf: int = 23  # 恒定质量因子 (0-51, 越低质量越好)
    preset: str = "medium"  # 编码预设

    # 分辨率
    width: int = DEFAULT_VIDEO_HEIGHT  # 竖屏短视频：宽 1080
    height: int = DEFAULT_VIDEO_WIDTH  # 竖屏短视频：高 1920
    fps: int = 30

    # 硬件加速
    use_hw_accel: bool = True
    hw_accel_type: str = "videotoolbox"  # videotoolbox (mac), nvenc, qsv


class VideoExporter:
    """
    视频文件导出器

    使用 FFmpeg 将项目导出为视频文件

    .. deprecated::
        推荐使用 :class:`DirectVideoExporter`，它提供更完整的功能：
        - 硬件加速支持 (NVIDIA, Intel, Apple, VAAPI)
        - 多种分辨率预设
        - 批量导出
        - 解说视频导出

    使用示例:
        from scenefab.services.export import DirectVideoExporter

        exporter = DirectVideoExporter()
    """

    def __init__(self, config: Optional["ExportConfig"] = None):
        warnings.warn(
            "VideoExporter is deprecated, use DirectVideoExporter instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.config = config or ExportConfig()
        self._executor = get_ffmpeg_executor()

    def export(
        self,
        video_path: str,
        audio_path: str | None = None,
        output_path: str = "output.mp4",
        subtitles_path: str | None = None,
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

        cmd = self._build_ffmpeg_command(video_path, audio_path, subtitles_path)
        cmd.append(str(output))

        result = self._executor.run(cmd, timeout=300)

        if result.returncode != 0:
            raise ExportError(
                message="导出失败",
                details={"stderr": result.stderr, "cmd": " ".join(cmd)},
            )

        return str(output)

    def _build_ffmpeg_command(
        self,
        video_path: str,
        audio_path: str | None,
        subtitles_path: str | None,
    ) -> list[str]:
        """构建 ffmpeg 命令行参数（不含输出路径与执行）"""
        cmd = ["ffmpeg", "-y"]

        self._add_input_args(cmd, video_path, audio_path)
        self._add_filter_args(cmd, subtitles_path)
        self._add_video_codec_args(cmd)
        self._add_video_quality_args(cmd)
        self._add_audio_codec_args(cmd)
        self._add_stream_mapping_args(cmd, audio_path)
        self._add_misc_args(cmd)

        return cmd

    @staticmethod
    def _add_input_args(cmd: list[str], video_path: str, audio_path: str | None) -> None:
        """添加输入参数"""
        cmd.extend(["-i", video_path])
        if audio_path:
            cmd.extend(["-i", audio_path])

    def _add_filter_args(self, cmd: list[str], subtitles_path: str | None) -> None:
        """添加视频滤镜参数（缩放、字幕烧录）"""
        filters = [f"scale={self.config.width}:{self.config.height}"]

        if subtitles_path and Path(subtitles_path).exists():
            # 使用 ass 滤镜烧录字幕
            filters.append(f"ass={subtitles_path}")

        if filters:
            cmd.extend(["-vf", ",".join(filters)])

    def _add_video_codec_args(self, cmd: list[str]) -> None:
        """添加视频编码器参数（硬件加速或软件编码）"""
        if self.config.use_hw_accel:
            cmd.extend(self._get_hw_accel_params())
        else:
            cmd.extend(["-c:v", self.config.video_codec.value])
            cmd.extend(["-preset", self.config.preset])
            cmd.extend(["-crf", str(self.config.crf)])

    def _add_video_quality_args(self, cmd: list[str]) -> None:
        """添加视频质量参数（码率、帧率）"""
        cmd.extend(["-b:v", self.config.video_bitrate])
        cmd.extend(["-r", str(self.config.fps)])

    def _add_audio_codec_args(self, cmd: list[str]) -> None:
        """添加音频编码器参数"""
        cmd.extend(["-c:a", self.config.audio_codec.value])
        cmd.extend(["-b:a", self.config.audio_bitrate])

    @staticmethod
    def _add_stream_mapping_args(cmd: list[str], audio_path: str | None) -> None:
        """添加流映射参数"""
        cmd.extend(["-map", "0:v:0"])
        if audio_path:
            cmd.extend(["-map", "1:a:0"])
        else:
            cmd.extend(["-map", "0:a:0?"])

    @staticmethod
    def _add_misc_args(cmd: list[str]) -> None:
        """添加其他杂项参数（-shortest、-movflags）"""
        cmd.extend(["-shortest"])
        cmd.extend(["-movflags", "+faststart"])

    # hw_accel_type → (codec_arg, extra_params)
    _HW_ACCEL_PARAMS: dict = {
        "videotoolbox": (["-c:v", "h264_videotoolbox", "-q:v", "60"], []),
        "nvenc": (["-c:v", "h264_nvenc"], ["-preset", "p4", "-cq"]),
        "qsv": (["-c:v", "h264_qsv"], ["-preset", "medium"]),
    }

    def _get_hw_accel_params(self) -> list[str]:
        """获取硬件加速参数"""
        hw_config = self._HW_ACCEL_PARAMS.get(self.config.hw_accel_type)
        if hw_config:
            codec_args, extra_args = hw_config
            params = list(codec_args)
            if self.config.hw_accel_type == "nvenc":
                params.extend(extra_args)
                params.append(str(self.config.crf))
            else:
                params.extend(extra_args)
            return params
        # 无硬件加速
        return [
            "-c:v",
            self.config.video_codec.value,
            "-preset",
            self.config.preset,
            "-crf",
            str(self.config.crf),
        ]

    def concat_videos(
        self,
        video_paths: list[str],
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
        with open(list_file, "w") as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output),
        ]

        result = self._executor.run(cmd, timeout=300)

        # 清理
        list_file.unlink(missing_ok=True)

        if result.returncode != 0:
            raise ExportError(message="拼接失败", details={"stderr": result.stderr})

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

        cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path]

        if mix_with_original:
            # 混合音频
            cmd.extend(
                [
                    "-filter_complex",
                    f"[0:a]volume={original_volume}[a0];"
                    f"[1:a]volume={audio_volume}[a1];"
                    f"[a0][a1]amix=inputs=2:duration=shortest[aout]",
                    "-map",
                    "0:v",
                    "-map",
                    "[aout]",
                ]
            )
        else:
            # 替换音频
            cmd.extend(
                [
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                ]
            )

        cmd.extend(
            [
                "-c:v",
                "copy",
                "-c:a",
                self.config.audio_codec.value,
                "-shortest",
                str(output),
            ]
        )

        result = self._executor.run(cmd, timeout=300)

        if result.returncode != 0:
            raise ExportError(message="添加音频失败", details={"stderr": result.stderr})

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
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            video_path,
            "-vframes",
            "1",
            "-vf",
            f"scale={width}:{height}",
            "-q:v",
            "2",
            str(output),
        ]

        result = self._executor.run(cmd, timeout=60)

        if result.returncode != 0:
            raise ExportError(
                message="创建缩略图失败", details={"stderr": result.stderr}
            )

        return str(output)
