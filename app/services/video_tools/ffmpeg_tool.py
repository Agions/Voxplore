"""
FFmpeg 工具模块

提供 FFmpeg/FFprobe 调用的公共工具函数
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
logger = logging.getLogger(__name__)
from typing import Optional, List, Dict, Any, Tuple


class FFmpegTool:
    """FFmpeg 工具类"""

    # ========== 基础检查 ==========

    @staticmethod
    def check_ffmpeg() -> None:
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg 不可用")
        except FileNotFoundError:
            raise RuntimeError("FFmpeg 未安装，请安装后重试")

    # ========== 视频信息获取 ==========

    @staticmethod
    def get_duration(video_path: str) -> float:
        """获取视频时长（秒）"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json', video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return float(data.get('format', {}).get('duration', 0))
        except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError):
            return 0.0

    @staticmethod
    def get_resolution(video_path: str) -> Tuple[int, int]:
        """获取视频分辨率 (width, height)"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-print_format', 'json',
            '-show_streams', video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    return (stream.get('width', 1920), stream.get('height', 1080))
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.debug(f"ffprobe resolution parse failed for {video_path}: {e}")
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

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            if streams:
                fps_str = streams[0].get('r_frame_rate', '30/1')
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    return float(num) / float(den) if den != '0' else 30.0
                return float(fps_str)
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
            logger.debug(f"ffprobe framerate parse failed for {video_path}: {e}")
        return 30.0

    @staticmethod
    def get_bitrate(video_path: str) -> int:
        """获取视频码率 (bps)"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=bit_rate',
            '-of', 'json', video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return int(data.get('format', {}).get('bit_rate', 0))
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
            return 0

    @staticmethod
    def get_video_info(video_path: str) -> Dict[str, Any]:
        """获取完整视频信息"""
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return {}

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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def concat_videos(
        input_paths: List[str],
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

            try:
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_path,
                    '-c', 'copy',
                    output_path,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
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
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.returncode == 0
            except subprocess.CalledProcessError:
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    # ========== 格式转换 ==========

    @staticmethod
    def convert_format(
        input_path: str,
        output_path: str,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        preset: str = "medium",
    ) -> bool:
        """
        转换视频格式

        Args:
            input_path: 输入路径
            output_path: 输出路径
            video_codec: 视频编码
            audio_codec: 音频编码
            preset: 编码预设 (ultrafast/slow 等)

        Returns:
            是否成功
        """
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', video_codec,
            '-c:a', audio_codec,
            '-preset', preset,
            output_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    # ========== 辅助方法 ==========

    @staticmethod
    def run_command(
        cmd: List[str],
        capture: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """运行 FFmpeg 命令"""
        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=check,
        )

    @staticmethod
    def parse_time_output(output: str, key: str) -> Optional[float]:
        """从 FFmpeg 输出解析时间值"""
        for line in output.split('\n'):
            if key in line:
                try:
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        return float(parts[1].strip())
                except (ValueError, IndexError):
                    continue
        return None


__all__ = ["FFmpegTool"]
