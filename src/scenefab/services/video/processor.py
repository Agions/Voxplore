"""
视频处理器模块

提供视频剪切、合并、音频混音等操作。
"""

from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    视频处理器
    优化的剪切、合并操作
    """

    @staticmethod
    def cut_video(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        quality: int = 23,
    ) -> bool:
        """剪切视频片段"""
        try:
            duration = end_time - start_time

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(start_time),
                    "-i",
                    input_path,
                    "-t",
                    str(duration),
                    "-c:v",
                    "libx264",
                    "-crf",
                    str(quality),
                    "-preset",
                    "fast",
                    "-c:a",
                    "aac",
                    "-strict",
                    "experimental",
                    "-avoid_negative_ts",
                    "make_zero",
                    output_path,
                ],
                capture_output=True,
                timeout=max(60, int(duration * 2)),
                check=True,
            )
            return True

        except subprocess.TimeoutExpired:
            logger.error("Video cutting timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Video cutting failed: {e}")
            return False

    @staticmethod
    def concatenate_videos(
        input_paths: list[str], output_path: str, temp_dir: str | None = None
    ) -> bool:
        """合并多个视频"""
        if not input_paths:
            return False

        if len(input_paths) == 1:
            try:
                import shutil

                shutil.copy(input_paths[0], output_path)
                return True
            except Exception as e:
                logger.error(f"File copy failed: {e}")
                return False

        if temp_dir is None:
            temp_dir = os.path.dirname(output_path) or "."

        list_file = os.path.join(temp_dir, "concat_list.txt")

        try:
            with open(list_file, "w") as f:
                for path in input_paths:
                    f.write(f"file '{path}'\n")

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_file,
                    "-c",
                    "copy",
                    output_path,
                ],
                capture_output=True,
                timeout=300,
                check=True,
            )

            return True

        except subprocess.TimeoutExpired:
            logger.error("Video concatenation timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Video concatenation failed: {e}")
            return False
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)

    @staticmethod
    def add_audio(
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_volume: float = 1.0,
        video_volume: float = 0.0,
    ) -> bool:
        """添加音频到视频（优化版 - 单次编码）"""
        try:
            # 使用 filter_complex 一次性完成，避免多次编码
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-i",
                    audio_path,
                    "-filter_complex",
                    f"[0:a]volume={video_volume}[a0];[1:a]volume={audio_volume}[a1];[a0][a1]amix=inputs=2:duration=longest[aout]",
                    "-map",
                    "0:v",
                    "-map",
                    "[aout]",
                    "-c:v",
                    "copy",  # 视频流直接复制，不重新编码
                    "-c:a",
                    "aac",
                    "-ar",
                    "44100",
                    output_path,
                ],
                capture_output=True,
                timeout=300,
                check=True,
            )
            return True

        except subprocess.TimeoutExpired:
            logger.error("Audio mixing timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio mixing failed: {e}")
            return False

    @staticmethod
    def extract_subclip(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        quality: int = 18,
    ) -> bool:
        """
        高质量提取子片段
        使用双次编码确保帧精确
        """
        try:
            duration = end_time - start_time

            # 第一步：精确裁剪
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(start_time),
                    "-i",
                    input_path,
                    "-t",
                    str(duration),
                    "-c:v",
                    "libx264",
                    "-crf",
                    str(quality),
                    "-preset",
                    "medium",
                    "-c:a",
                    "aac",
                    "-strict",
                    "experimental",
                    "-avoid_negative_ts",
                    "make_zero",
                    output_path,
                ],
                capture_output=True,
                timeout=max(60, int(duration * 3)),
                check=True,
            )
            return True

        except subprocess.TimeoutExpired:
            logger.error("Subclip extraction timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Subclip extraction failed: {e}")
            return False


__all__ = ["VideoProcessor"]
