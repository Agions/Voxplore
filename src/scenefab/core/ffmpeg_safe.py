#!/usr/bin/env python3
"""
FFmpeg 安全封装 — v2.0 重构

提供白名单参数校验的 FFmpeg 命令构建器，彻底消除命令注入风险。

特性:
- 参数白名单（codec / preset / crf / 滤镜）
- 路径安全检查（禁止写入系统目录）
- 危险字符检测（; & | ` $ ( ) 等）
- 使用 subprocess list 模式（非 shell）
- 审计日志自动集成

使用示例:
    from scenefab.core.ffmpeg_safe import SafeFFmpegCommand

    cmd = SafeFFmpegCommand(
        input_file=Path("input.mp4"),
        output_file=Path("output.mp4"),
        codec="libx264",
        preset="medium",
        crf=23,
    )
    result = cmd.execute()
"""

import logging
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from scenefab.core.audit import AuditLogger

logger = logging.getLogger(__name__)


# ============================================
# 白名单 & 黑名单
# ============================================

ALLOWED_CODECS = {
    "libx264",
    "libx265",
    "libvpx-vp9",
    "libvpx",
    "h264_nvenc",
    "hevc_nvenc",  # NVIDIA GPU
    "h264_qsv",
    "hevc_qsv",  # Intel Quick Sync
    "h264_videotoolbox",
    "hevc_videotoolbox",  # macOS
    "copy",  # 流复制（不重新编码）
    "png",
    "mjpeg",  # 帧提取
    "aac",
    "libmp3lame",
    "libopus",  # 音频
}

ALLOWED_PRESETS = {
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
}

ALLOWED_PIX_FMTS = {
    "yuv420p",
    "yuv444p",
    "yuvj420p",
    "rgb24",
    "rgba",
    "nv12",
    "yuv420p10le",
}

CRF_RANGE = (0, 51)
BITRATE_MAX_MBPS = 100  # 上限 100 Mbps

# 危险字符：除路径分隔符外的特殊 shell 元字符
_DANGEROUS_CHARS = re.compile(r'[;&|`$(){}\[\]!<>\\\n\r"\'\x00]')

# 禁止写入的系统目录
_FORBIDDEN_OUTPUT_DIRS = (
    "/etc",
    "/bin",
    "/sbin",
    "/usr",
    "/boot",
    "/lib",
    "/lib64",
    "/sys",
    "/proc",
    "/dev",
    "/root",
    "/var/log",
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
)


# ============================================
# 数据模型
# ============================================


@dataclass
class FFmpegResult:
    """FFmpeg 执行结果"""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    command: list[str]
    output_path: Path | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "returncode": self.returncode,
            "stdout": self.stdout[:2000],  # 截断
            "stderr": self.stderr[:2000],
            "duration_ms": self.duration_ms,
            "command": self.command,
            "output_path": str(self.output_path) if self.output_path else None,
        }


# ============================================
# 主类
# ============================================


class FFmpegSecurityError(ValueError):
    """FFmpeg 安全校验失败"""


@dataclass
class SafeFFmpegCommand:
    """
    安全的 FFmpeg 命令构建器

    所有参数经白名单校验，路径经安全检查
    """

    input_file: Path
    output_file: Path
    codec: str = "libx264"
    preset: str = "medium"
    crf: int = 23
    pix_fmt: str = "yuv420p"
    bitrate_mbps: float | None = None  # 覆盖 CRF
    filters: list[str] = field(default_factory=list)
    audio_codec: str = "aac"
    audio_bitrate_kbps: int = 192
    extra_args: list[str] = field(default_factory=list)
    timeout_sec: int = 600
    hwaccel: str | None = None  # "cuda" / "qsv" / "videotoolbox" / None

    # ==============================================================
    # 校验
    # ==============================================================

    def validate(self) -> None:
        """
        校验所有参数，不通过则抛出 FFmpegSecurityError
        """
        # 1. 输入文件存在
        if not self.input_file.exists():
            raise FFmpegSecurityError(f"Input file not found: {self.input_file}")
        if not self.input_file.is_file():
            raise FFmpegSecurityError(f"Input is not a file: {self.input_file}")

        # 2. 输出路径安全
        out_path = Path(self.output_file).absolute()
        out_str = str(out_path).lower()
        for forbidden in _FORBIDDEN_OUTPUT_DIRS:
            if forbidden in out_str:
                raise FFmpegSecurityError(
                    f"Output path rejected (forbidden directory): {out_path}"
                )
        # 路径不能包含危险字符
        if _DANGEROUS_CHARS.search(out_str):
            raise FFmpegSecurityError(
                f"Output path contains dangerous characters: {out_path}"
            )

        # 3. 参数白名单
        if self.codec not in ALLOWED_CODECS:
            raise FFmpegSecurityError(
                f"Codec '{self.codec}' not in whitelist. "
                f"Allowed: {sorted(ALLOWED_CODECS)}"
            )
        if self.preset not in ALLOWED_PRESETS:
            raise FFmpegSecurityError(
                f"Preset '{self.preset}' not in whitelist. "
                f"Allowed: {sorted(ALLOWED_PRESETS)}"
            )
        if self.pix_fmt not in ALLOWED_PIX_FMTS:
            raise FFmpegSecurityError(f"Pixel format '{self.pix_fmt}' not in whitelist")
        if not (CRF_RANGE[0] <= self.crf <= CRF_RANGE[1]):
            raise FFmpegSecurityError(
                f"CRF {self.crf} out of range [{CRF_RANGE[0]}, {CRF_RANGE[1]}]"
            )
        if self.bitrate_mbps is not None:
            if not (0.1 <= self.bitrate_mbps <= BITRATE_MAX_MBPS):
                raise FFmpegSecurityError(
                    f"Bitrate {self.bitrate_mbps} Mbps out of range "
                    f"[0.1, {BITRATE_MAX_MBPS}]"
                )
        if self.audio_codec not in ALLOWED_CODECS:
            raise FFmpegSecurityError(
                f"Audio codec '{self.audio_codec}' not in whitelist"
            )
        if not (32 <= self.audio_bitrate_kbps <= 512):
            raise FFmpegSecurityError(
                f"Audio bitrate {self.audio_bitrate_kbps} kbps out of range [32, 512]"
            )

        # 4. 滤镜安全检查
        for f in self.filters:
            if _DANGEROUS_CHARS.search(f):
                raise FFmpegSecurityError(
                    f"Filter contains dangerous characters: {f!r}"
                )

        # 5. extra_args 安全检查
        for arg in self.extra_args:
            if _DANGEROUS_CHARS.search(arg):
                raise FFmpegSecurityError(
                    f"Extra arg contains dangerous characters: {arg!r}"
                )

        # 6. hwaccel 白名单
        if self.hwaccel is not None and self.hwaccel not in (
            "cuda",
            "qsv",
            "videotoolbox",
        ):
            raise FFmpegSecurityError(
                f"HW accel '{self.hwaccel}' not in whitelist [cuda, qsv, videotoolbox]"
            )

    # ==============================================================
    # 构建
    # ==============================================================

    def build(self) -> list[str]:
        """构建 FFmpeg 命令（不执行）"""
        self.validate()
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]

        # 硬件加速
        if self.hwaccel:
            cmd.extend(["-hwaccel", self.hwaccel])

        # 输入
        cmd.extend(["-i", str(Path(self.input_file).absolute())])

        # 视频编码
        if self.codec != "copy":
            cmd.extend(["-c:v", self.codec])
            if self.codec not in ("png", "mjpeg"):
                cmd.extend(["-preset", self.preset])
                if self.bitrate_mbps is not None:
                    cmd.extend(["-b:v", f"{self.bitrate_mbps}M"])
                else:
                    cmd.extend(["-crf", str(self.crf)])
            cmd.extend(["-pix_fmt", self.pix_fmt])

        # 滤镜
        if self.filters:
            cmd.extend(["-vf", ",".join(self.filters)])

        # 音频编码
        cmd.extend(["-c:a", self.audio_codec])
        if self.audio_codec != "copy":
            cmd.extend(["-b:a", f"{self.audio_bitrate_kbps}k"])

        # 额外参数（已校验）
        cmd.extend(self.extra_args)

        # 输出
        cmd.append(str(Path(self.output_file).absolute()))

        return cmd

    # ==============================================================
    # 执行
    # ==============================================================

    def execute(self, audit: bool = True) -> FFmpegResult:
        """
        安全执行 FFmpeg

        Args:
            audit: 是否记录到审计日志

        Returns:
            FFmpegResult
        """
        import time

        cmd = self.build()  # 已校验
        start_ms = int(time.time() * 1000)
        logger.info(f"FFmpeg execute: {' '.join(shlex.quote(c) for c in cmd[:6])}...")

        if audit:
            AuditLogger().log_action(
                action="ffmpeg_execute",
                parameters={
                    "input": str(self.input_file.absolute()),
                    "output": str(self.output_file.absolute()),
                    "codec": self.codec,
                    "preset": self.preset,
                    "crf": self.crf,
                    "filters": self.filters,
                    "hwaccel": self.hwaccel,
                },
            )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
                # 关键：不用 shell=True
            )
            duration_ms = int(time.time() * 1000) - start_ms
            success = result.returncode == 0

            if audit:
                AuditLogger().log_action(
                    action="ffmpeg_execute_done",
                    parameters={
                        "input": str(self.input_file.absolute()),
                        "output": str(self.output_file.absolute()),
                    },
                    result="success" if success else "failure",
                    duration_ms=duration_ms,
                    error_message=result.stderr[:500] if not success else "",
                    error_type="FFmpegError" if not success else "",
                )

            if not success:
                logger.error(
                    f"FFmpeg failed (rc={result.returncode}): {result.stderr[:500]}"
                )

            return FFmpegResult(
                success=success,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=duration_ms,
                command=cmd,
                output_path=self.output_file if success else None,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int(time.time() * 1000) - start_ms
            logger.error(f"FFmpeg timeout after {self.timeout_sec}s")
            if audit:
                AuditLogger().log_action(
                    action="ffmpeg_execute_timeout",
                    parameters={"input": str(self.input_file.absolute())},
                    result="failure",
                    duration_ms=duration_ms,
                    error_message=f"Timeout after {self.timeout_sec}s",
                    error_type="TimeoutExpired",
                )
            raise
        except Exception as e:
            duration_ms = int(time.time() * 1000) - start_ms
            logger.error(f"FFmpeg execution failed: {e}")
            if audit:
                AuditLogger().log_action(
                    action="ffmpeg_execute_error",
                    parameters={"input": str(self.input_file.absolute())},
                    result="failure",
                    duration_ms=duration_ms,
                    error_message=str(e),
                    error_type=type(e).__name__,
                )
            raise


# ============================================
# 工具函数
# ============================================


def is_safe_path(path: str | Path, allowed_bases: list[Path] | None = None) -> bool:
    """
    检查路径是否安全（不指向系统目录、不含危险字符）

    Args:
        path: 待检查路径
        allowed_bases: 允许的基础目录列表（None 表示任何用户可写目录）

    Returns:
        True 安全 / False 不安全
    """
    try:
        p = Path(path).absolute()
        p_str = str(p).lower()
    except Exception:
        return False

    # 系统目录检查
    for forbidden in _FORBIDDEN_OUTPUT_DIRS:
        if forbidden in p_str:
            return False

    # 危险字符
    if _DANGEROUS_CHARS.search(p_str):
        return False

    # 基础目录限制
    if allowed_bases is not None:
        try:
            p.relative_to(*[Path(b).absolute() for b in allowed_bases])
        except ValueError:
            return False

    return True


__all__ = [
    "SafeFFmpegCommand",
    "FFmpegResult",
    "FFmpegSecurityError",
    "is_safe_path",
    "ALLOWED_CODECS",
    "ALLOWED_PRESETS",
]
