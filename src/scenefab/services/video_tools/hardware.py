"""FFmpeg 硬件加速检测。

从 ffmpeg_tool 拆出（P3 后续）。提供 `HWAccelType` 枚举与平台无关的
硬件加速检测函数。FFmpeg 编码器支持探测经统一安全执行器；
nvidia-smi / wmic 等非 ffmpeg 能力探测保留裸 subprocess（不在白名单内）。
"""

from __future__ import annotations

import logging
import platform
import subprocess
from enum import Enum
from pathlib import Path

from ...utils.security import SecurityError, get_ffmpeg_executor

logger = logging.getLogger(__name__)


class HWAccelType(Enum):
    """硬件加速类型"""

    NONE = "none"
    NVIDIA = "nvenc"  # NVIDIA NVENC
    INTEL = "qsv"  # Intel Quick Sync
    AMD = "amf"  # AMD AMF
    APPLE = "videotoolbox"  # Apple VideoToolbox (macOS)
    VAAPI = "vaapi"  # Linux VAAPI

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


def ffmpeg_supports_encoder(encoder: str) -> bool:
    """检查 FFmpeg 是否支持指定编码器（经安全执行器）。"""
    try:
        result = get_ffmpeg_executor().run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            timeout=10,
        )
        return result.returncode == 0 and encoder in (result.stdout or "")
    except (SecurityError, FileNotFoundError):
        return False


def check_nvidia_smi() -> bool:
    """检测 NVIDIA GPU 和 NVENC 支持。

    nvidia-smi 不在 ffmpeg 安全执行器白名单内，作为只读能力探测保留
    裸 subprocess；FFmpeg 编码器支持检查走统一执行器。
    """
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return ffmpeg_supports_encoder("h264_nvenc")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def check_vaapi() -> bool:
    """检测 VAAPI 支持"""
    # 检查 /dev/dri/ 是否存在 (Linux 硬件设备)
    if Path("/dev/dri/").exists():
        return ffmpeg_supports_encoder("vaapi")
    return False


def check_intel_cpu() -> bool:
    """检测 Intel CPU (用于 QSV)"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True,
                timeout=5,
            )
            return "Intel" in result.stdout.decode("utf-8", errors="ignore")
        else:
            # Linux/macOS 下检测 /proc/cpuinfo
            with open("/proc/cpuinfo") as f:
                return "genuineintel" in f.read().lower()
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug(f"CPU vendor detection failed: {e}")
    return False


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
        if check_nvidia_smi():
            return HWAccelType.NVIDIA

        # 检测 VAAPI
        if check_vaapi():
            return HWAccelType.VAAPI

    # Windows - 优先 NVENC
    if system == "Windows":
        if check_nvidia_smi():
            return HWAccelType.NVIDIA

        # 检测 Intel QSV (通过 CPU 检测)
        if check_intel_cpu():
            return HWAccelType.INTEL

    return HWAccelType.NONE


def get_hw_accel_encoder(codec: str = "libx264") -> tuple[str, str | None]:
    """获取最佳可用的视频编码器

    Args:
        codec: 原始编码器 (libx264, libx265)

    Returns:
        (encoder_name, hwaccel_arg) 元组，如果无硬件加速则返回 (codec, None)
    """
    hw_type = detect_hw_accel()

    if hw_type == HWAccelType.NONE:
        return codec, None

    # 获取对应的硬件编码器
    hw_encoder = hw_type.get_encoder(codec)
    if hw_encoder:
        return hw_encoder, hw_type.ffmpeg_hwaccel

    return codec, None


__all__ = [
    "HWAccelType",
    "detect_hw_accel",
    "get_hw_accel_encoder",
    "ffmpeg_supports_encoder",
    "check_nvidia_smi",
    "check_vaapi",
    "check_intel_cpu",
]
