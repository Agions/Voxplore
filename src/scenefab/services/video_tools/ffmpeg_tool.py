"""
FFmpeg 工具模块

提供 FFmpeg/FFprobe 调用的公共工具函数
"""

import json
import logging
import platform
import subprocess
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any

from ...utils.security import SecurityError, get_ffmpeg_executor

logger = logging.getLogger(__name__)


class HWAccelType(Enum):
    """硬件加速类型"""
    NONE = "none"
    NVIDIA = "nvenc"           # NVIDIA NVENC
    INTEL = "qsv"              # Intel Quick Sync
    AMD = "amf"                # AMD AMF
    APPLE = "videotoolbox"     # Apple VideoToolbox (macOS)
    VAAPI = "vaapi"            # Linux VAAPI

    @property
    def ffmpeg_hwaccel(self) -> str | None:
        """获取 ffmpeg -hwaccel 参数值"""
        mapping = {
            HWAccelType.NVIDIA: "cuda",
            HWAccelType.APPLE: "videotoolbox",
            HWAccelType.INTEL: "qsv",
            HWAccelType.AMD: "amf",
            HWAccelType.VAAPI: "vaapi",
        }
        return mapping.get(self)

    def get_encoder(self, codec: str) -> str | None:
        """获取硬件加速的编码器名称

        Args:
            codec: 原始编码器 (libx264, libx265 等)

        Returns:
            硬件加速编码器名称或 None
        """
        encoder_map = {
            HWAccelType.NVIDIA: {
                "libx264": "h264_nvenc",
                "libx265": "hevc_nvenc",
            },
            HWAccelType.APPLE: {
                "libx264": "h264_videotoolbox",
                "libx265": "hevc_videotoolbox",
            },
            HWAccelType.INTEL: {
                "libx264": "h264_qsv",
                "libx265": "hevc_qsv",
            },
            HWAccelType.AMD: {
                "libx264": "h264_amf",
                "libx265": "hevc_amf",
            },
            HWAccelType.VAAPI: {
                "libx264": "h264_vaapi",
                "libx265": "hevc_vaapi",
            },
        }
        return encoder_map.get(self, {}).get(codec)


class FFmpegTool:
    """FFmpeg 工具类"""

    # 类级别安全执行器（复用全局单例）
    _executor = get_ffmpeg_executor()

    # ========== 基础检查 ==========

    @staticmethod
    def check_ffmpeg() -> None:
        """检查 FFmpeg 是否可用"""
        try:
            result = FFmpegTool._executor.run(
                ['ffmpeg', '-version'],
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg 不可用")
        except FileNotFoundError:
            raise RuntimeError("FFmpeg 未安装，请安装后重试")

    # ========== 硬件加速检测 ==========

    @staticmethod
    def detect_hw_accel() -> HWAccelType:
        """自动检测可用的硬件加速

        优先级: NVENC > VAAPI > VideoToolbox > QSV > CPU

        Returns:
            HWAccelType: 检测到的硬件加速类型
        """
        system = platform.system()

        # macOS - 优先 VideoToolbox
        if system == "Darwin":
            return HWAccelType.APPLE

        # Linux - 检测 VAAPI 和 NVENC
        if system == "Linux":
            # 优先检测 NVIDIA
            if FFmpegTool._check_nvidia_smi():
                return HWAccelType.NVIDIA

            # 检测 VAAPI
            if FFmpegTool._check_vaapi():
                return HWAccelType.VAAPI

        # Windows - 优先 NVENC
        if system == "Windows":
            if FFmpegTool._check_nvidia_smi():
                return HWAccelType.NVIDIA

            # 检测 Intel QSV (通过 CPU 检测)
            if FFmpegTool._check_intel_cpu():
                return HWAccelType.INTEL

        return HWAccelType.NONE

    @staticmethod
    def _check_nvidia_smi() -> bool:
        """检测 NVIDIA GPU 和 NVENC 支持"""
        try:
            result = subprocess.run(
                ['nvidia-smi'],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                # 进一步检查 FFmpeg 是否支持 h264_nvenc
                enc_result = subprocess.run(
                    ['ffmpeg', '-hide_banner', '-encoders'],
                    capture_output=True,
                    timeout=10,
                )
                if 'h264_nvenc' in enc_result.stdout.decode('utf-8', errors='ignore'):
                    return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False

    @staticmethod
    def _check_vaapi() -> bool:
        """检测 VAAPI 支持"""
        try:
            # 检查 /dev/dri/ 是否存在 (Linux 硬件设备)
            if Path('/dev/dri/').exists():
                # 检查 FFmpeg 是否支持 vaapi
                result = subprocess.run(
                    ['ffmpeg', '-hide_banner', '-encoders'],
                    capture_output=True,
                    timeout=10,
                )
                if 'vaapi' in result.stdout.decode('utf-8', errors='ignore'):
                    return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False

    @staticmethod
    def _check_intel_cpu() -> bool:
        """检测 Intel CPU (用于 QSV)"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'name'],
                    capture_output=True,
                    timeout=5,
                )
                return "Intel" in result.stdout.decode('utf-8', errors='ignore')
            else:
                # Linux/macOS 下检测 /proc/cpuinfo
                with open('/proc/cpuinfo') as f:
                    return 'genuineintel' in f.read().lower()
        except Exception:
            pass
        return False

    @staticmethod
    def get_hw_accel_encoder(codec: str = "libx264") -> tuple[str, str | None]:
        """获取最佳可用的视频编码器

        Args:
            codec: 原始编码器 (libx264, libx265)

        Returns:
            (encoder_name, hwaccel_arg) 元组，如果无硬件加速则返回 (codec, None)
        """
        hw_type = FFmpegTool.detect_hw_accel()

        if hw_type == HWAccelType.NONE:
            return codec, None

        # 获取对应的硬件编码器
        hw_encoder = hw_type.get_encoder(codec)
        if hw_encoder:
            return hw_encoder, hw_type.ffmpeg_hwaccel

        return codec, None

    # ========== 视频信息获取 ==========

    @staticmethod
    def _run_ffprobe_json(cmd: list[str], timeout: int = 30) -> dict | None:
        """Run ffprobe command and return parsed JSON, or None on failure."""
        try:
            result = FFmpegTool._executor.run(cmd, timeout=timeout)
            if result.returncode != 0:
                return None
            return json.loads(result.stdout)
        except (SecurityError, json.JSONDecodeError):
            return None

    @staticmethod
    def get_duration(video_path: str) -> float:
        """获取视频时长（秒）"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json', video_path
        ]
        data = FFmpegTool._run_ffprobe_json(cmd)
        if data is None:
            return 0.0
        return float(data.get('format', {}).get('duration', 0))

    @staticmethod
    def get_resolution(video_path: str) -> tuple[int, int]:
        """获取视频分辨率 (width, height)"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-print_format', 'json',
            '-show_streams', video_path
        ]
        data = FFmpegTool._run_ffprobe_json(cmd)
        if data is None:
            return (1920, 1080)
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                return (stream.get('width', 1920), stream.get('height', 1080))
        return (1920, 1080)

    @staticmethod
    def get_framerate(video_path: str) -> float:
        """获取视频帧率"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'json', video_path
        ]
        data = FFmpegTool._run_ffprobe_json(cmd)
        if data is None:
            return 30.0
        streams = data.get('streams', [])
        if streams:
            fps_str = streams[0].get('r_frame_rate', '30/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return float(num) / float(den) if den != '0' else 30.0
            return float(fps_str)
        return 30.0

    @staticmethod
    def get_bitrate(video_path: str) -> int:
        """获取视频码率 (bps)"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=bit_rate',
            '-of', 'json', video_path
        ]
        data = FFmpegTool._run_ffprobe_json(cmd)
        if data is None:
            return 0
        return int(data.get('format', {}).get('bit_rate', 0))

    @staticmethod
    def get_video_info(video_path: str) -> dict[str, Any]:
        """获取完整视频信息"""
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        return FFmpegTool._run_ffprobe_json(cmd) or {}

    # ========== 视频处理 ==========

    @staticmethod
    def trim_video(
        input_path: str,
        output_path: str,
        start: float,
        end: float,
    ) -> bool:
        """
        裁剪视频

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            start: 开始时间（秒）
            end: 结束时间（秒）

        Returns:
            是否成功
        """
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-to', str(end),
            '-i', input_path,
            '-c', 'copy',
            output_path,
        ]

        try:
            result = FFmpegTool._executor.run(cmd, timeout=300)
            return result.returncode == 0
        except SecurityError:
            return False

    @staticmethod
    def concat_videos(
        input_paths: list[str],
        output_path: str,
        method: str = "concat",
    ) -> bool:
        """
        拼接视频

        Args:
            input_paths: 输入视频路径列表
            output_path: 输出视频路径
            method: concat/demuxer

        Returns:
            是否成功
        """
        if method == "concat":
            # 使用 concat 协议（适用于相同编码的视频）
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for p in input_paths:
                    f.write(f"file '{p}'\n")
                list_path = f.name

            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_path,
                '-c', 'copy',
                output_path,
            ]

            try:
                result = FFmpegTool._executor.run(cmd, timeout=600)
                return result.returncode == 0
            finally:
                Path(list_path).unlink(missing_ok=True)
        else:
            # 使用 concat demuxer（通用方式）
            filter_str = ''.join([f"[{i}:v][{i}:a]" for i in range(len(input_paths))])

            cmd = ['ffmpeg', '-y']
            for p in input_paths:
                cmd.extend(['-i', p])

            cmd.extend([
                '-filter_complex', f"{filter_str}concat=n={len(input_paths)}:v=1:a=1[v][a]",
                '-map', '[v]',
                '-map', '[a]',
                output_path,
            ])

            try:
                result = FFmpegTool._executor.run(cmd, timeout=600)
                return result.returncode == 0
            except SecurityError:
                return False

    @staticmethod
    def change_speed(
        input_path: str,
        output_path: str,
        speed: float,
    ) -> bool:
        """
        改变视频速度

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            speed: 速度倍数 (0.5=慢放, 2.0=快进)

        Returns:
            是否成功
        """
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-filter:v', f'setpts={1/speed}*PTS',
            '-filter:a', f'atempo={speed}',
            output_path,
        ]

        try:
            result = FFmpegTool._executor.run(cmd, timeout=300)
            return result.returncode == 0
        except SecurityError:
            return False

    @staticmethod
    def reverse_video(
        input_path: str,
        output_path: str,
    ) -> bool:
        """
        倒放视频

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径

        Returns:
            是否成功
        """
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-vf', 'reverse',
            '-af', 'areverse',
            output_path,
        ]

        try:
            result = FFmpegTool._executor.run(cmd, timeout=300)
            return result.returncode == 0
        except SecurityError:
            return False

    # ========== 音频处理 ==========

    @staticmethod
    def extract_audio(
        input_path: str,
        output_path: str,
        format: str = "mp3",
    ) -> bool:
        """
        提取音频

        Args:
            input_path: 输入视频路径
            output_path: 输出音频路径
            format: 音频格式 (mp3/aac/wav)

        Returns:
            是否成功
        """
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-vn',
            '-acodec', 'copy' if format == 'copy' else format,
            output_path,
        ]

        try:
            result = FFmpegTool._executor.run(cmd, timeout=300)
            return result.returncode == 0
        except SecurityError:
            return False

    @staticmethod
    def add_audio(
        video_path: str,
        audio_path: str,
        output_path: str,
        mix: bool = True,
        audio_volume: float = 1.0,
    ) -> bool:
        """
        添加音频到视频

        Args:
            video_path: 视频路径
            audio_path: 音频路径
            output_path: 输出路径
            mix: 是否混合原音频
            audio_volume: 音频音量 (0.0-1.0)

        Returns:
            是否成功
        """
        if mix:
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-filter_complex',
                f'[1:a]volume={audio_volume}[a]',
                '-map', '0:v',
                '-map', '[a]',
                '-shortest',
                output_path,
            ]
        else:
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-filter_complex',
                f'[1:a]volume={audio_volume}[a]',
                '-map', '0:v',
                '-map', '[a]',
                '-c:v', 'copy',
                '-shortest',
                output_path,
            ]

        try:
            result = FFmpegTool._executor.run(cmd, timeout=300)
            return result.returncode == 0
        except SecurityError:
            return False

    @staticmethod
    def adjust_volume(
        input_path: str,
        output_path: str,
        volume: float,
    ) -> bool:
        """
        调整音量

        Args:
            input_path: 输入路径
            output_path: 输出路径
            volume: 音量倍数 (0.5=一半, 2.0=两倍)

        Returns:
            是否成功
        """
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-af', f'volume={volume}',
            output_path,
        ]

        try:
            result = FFmpegTool._executor.run(cmd, timeout=300)
            return result.returncode == 0
        except SecurityError:
            return False

    # ========== 缩略图 ==========

    @staticmethod
    def generate_thumbnail(
        video_path: str,
        output_path: str,
        timestamp: float = 1.0,
        width: int = 320,
        height: int = 180,
    ) -> bool:
        """
        生成缩略图

        Args:
            video_path: 视频路径
            output_path: 输出图片路径
            timestamp: 时间点（秒）
            width: 输出宽度
            height: 输出高度

        Returns:
            是否成功
        """
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-vf', f'scale={width}:{height}',
            '-q:v', '2',
            output_path,
        ]

        try:
            result = FFmpegTool._executor.run(cmd, timeout=120)
            return result.returncode == 0
        except SecurityError:
            return False

    @staticmethod
    def generate_waveform(
        audio_path: str,
        output_path: str,
        width: int = 800,
        height: int = 200,
    ) -> bool:
        """
        生成音频波形图

        Args:
            audio_path: 音频路径
            output_path: 输出图片路径
            width: 宽度
            height: 高度

        Returns:
            是否成功
        """
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-filter_complex',
            f'aformat=channel_layouts=mono,showwavespic=s={width}x{height}',
            '-frames:v', '1',
            '-png', output_path,
        ]

        try:
            result = FFmpegTool._executor.run(cmd, timeout=120)
            return result.returncode == 0
        except SecurityError:
            return False

    # ========== 格式转换 ==========

    @staticmethod
    def convert_format(
        input_path: str,
        output_path: str,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        preset: str = "medium",
        use_hw_accel: bool = True,
    ) -> bool:
        """
        转换视频格式

        Args:
            input_path: 输入路径
            output_path: 输出路径
            video_codec: 视频编码
            audio_codec: 音频编码
            preset: 编码预设 (ultrafast/slow 等)
            use_hw_accel: 是否使用硬件加速

        Returns:
            是否成功
        """
        cmd = ['ffmpeg', '-y']

        # 自动检测硬件加速
        if use_hw_accel:
            encoder, hwaccel = FFmpegTool.get_hw_accel_encoder(video_codec)
            if hwaccel:
                cmd.extend(['-hwaccel', hwaccel])
            cmd.extend(['-c:v', encoder])
        else:
            cmd.extend(['-c:v', video_codec])

        cmd.extend(['-i', input_path])
        cmd.extend(['-c:a', audio_codec])

        # 仅在 CPU 编码时使用 preset，硬件编码器有自己的质量设置
        if not use_hw_accel or FFmpegTool.detect_hw_accel() == HWAccelType.NONE:
            cmd.extend(['-preset', preset])

        cmd.append(output_path)

        try:
            result = FFmpegTool._executor.run(cmd, timeout=300)
            return result.returncode == 0
        except SecurityError:
            return False

    # ========== 辅助方法 ==========

    # ========== 异步 API（实验性） ==========

    @staticmethod
    async def run_async(
        args: list[str],
        timeout: float = 300.0,
    ) -> int:
        """
        异步执行 ffmpeg 命令（非阻塞）。

        示例:
            await FFmpegTool.run_async(['-i', 'in.mp4', '-c:v', 'libx264', 'out.mp4'])
        """
        from scenefab.utils.async_subprocess import run_ffmpeg
        return await run_ffmpeg(args, timeout=timeout)

    @staticmethod
    async def probe_async(
        video_path: str | Path,
        timeout: float = 30.0,
    ) -> dict[str, str]:
        """异步 ffprobe 探测视频元信息"""
        from scenefab.utils.async_subprocess import run_ffprobe
        return await run_ffprobe(video_path, timeout=timeout)


__all__ = ["FFmpegTool", "HWAccelType"]
