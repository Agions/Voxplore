"""FFprobe 视频元数据探测。

从 ffmpeg_tool 拆出（P3 后续）。所有 ffprobe 调用经统一安全执行器
（`utils.security.get_ffmpeg_executor`）。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ...utils.security import SecurityError, get_ffmpeg_executor

logger = logging.getLogger(__name__)


def run_ffprobe_json(cmd: list[str], timeout: int = 30) -> dict | None:
    """Run ffprobe command and return parsed JSON, or None on failure."""
    try:
        result = get_ffmpeg_executor().run(cmd, timeout=timeout)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)  # type: ignore[no-any-return]
    except (SecurityError, json.JSONDecodeError):
        return None


def get_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        video_path,
    ]
    data = run_ffprobe_json(cmd)
    if data is None:
        return 0.0
    return float(data.get("format", {}).get("duration", 0))


def get_resolution(video_path: str) -> tuple[int, int]:
    """获取视频分辨率 (width, height)"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        video_path,
    ]
    data = run_ffprobe_json(cmd)
    if data is None:
        return (1920, 1080)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            return (stream.get("width", 1920), stream.get("height", 1080))
    return (1920, 1080)


def get_framerate(video_path: str) -> float:
    """获取视频帧率"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "json",
        video_path,
    ]
    data = run_ffprobe_json(cmd)
    if data is None:
        return 30.0
    streams = data.get("streams", [])
    if streams:
        fps_str = streams[0].get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return float(num) / float(den) if den != "0" else 30.0
        return float(fps_str)
    return 30.0


def get_bitrate(video_path: str) -> int:
    """获取视频码率 (bps)"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=bit_rate",
        "-of",
        "json",
        video_path,
    ]
    data = run_ffprobe_json(cmd)
    if data is None:
        return 0
    return int(data.get("format", {}).get("bit_rate", 0))


def get_video_info(video_path: str) -> dict[str, Any]:
    """获取完整视频信息"""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    return run_ffprobe_json(cmd) or {}


__all__ = [
    "run_ffprobe_json",
    "get_duration",
    "get_resolution",
    "get_framerate",
    "get_bitrate",
    "get_video_info",
]
