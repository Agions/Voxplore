#!/usr/bin/env python3
"""
FFmpeg 安全封装 — v2.0 重构

提供白名单参数校验的 FFmpeg 命令构建器，彻底消除命令注入风险。

特性:
- 参数白名单（codec / preset / crf / 滤镜）
- 路径安全检查（禁止写入系统目录）
- 危险字符检测（; & | ` $ ( ) 等）
- 执行统一委托给 `utils.security.SecureExecutor`（单一安全执行底座，
  list 模式非 shell），本模块只负责声明式命令构建 + 结果/审计封装
- 审计日志自动集成

使用示例:
    from app.core.ffmpeg_safe import SafeFFmpegCommand

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
import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from app.core.audit import AuditLogger

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
# POSIX 列表（开头必须是 ``/``）；Windows 列表使用 ``c:\\`` 前缀。
# Phase 1 · SEC-06 修复后通过逐级匹配上级路径避免 path traversal 绕过。
_FORBIDDEN_POSIX_DIRS: tuple[str, ...] = (
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
)
_FORBIDDEN_WINDOWS_DIRS: tuple[str, ...] = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
)

# 保留旧名以免向下游调用方 ``_FORBIDDEN_OUTPUT_DIRS`` 产生 ImportError。
_FORBIDDEN_OUTPUT_DIRS: tuple[str, ...] = (
    *_FORBIDDEN_POSIX_DIRS,
    *_FORBIDDEN_WINDOWS_DIRS,
)


def _normalize_for_compare(path: str | Path) -> str:
    """跨平台路径规范化（用于目录黑名单匹配）。

    小写 + 替换反斜杠 + 去除尾部斜杠。
    """
    return str(path).replace("\\", "/").strip("/").rstrip("/").lower()


def _is_under_forbidden(path: Path) -> bool:
    """返回给定路径是否位于 :data:`_FORBIDDEN_OUTPUT_DIRS` 任何一项之下。

    Phase 1 · SEC-06 修复点：

    * 必须先用 :py:func:`os.path.normpath` 预处理输入路径，展开 ``..``
      与 ``.`` 段；这能避免 :py:meth:`Path.absolute` 与
      :py:meth:`Path.resolve` 在某些平台（路径不存在或 macOS 的
      ``/etc -> /private/etc`` 符号链接）下的意外行为；
    * 必须逐级比较上级路径（不再用字符串包含）；
    * Windows 路径使用 *盘符* + *路径元素* 的元组匹配，避免
      ``c:\\windows`` 子串被 ``c:\\windows_backup`` 误判。
    """

    posix_forbidden = {
        _normalize_for_compare(d) for d in _FORBIDDEN_POSIX_DIRS
    }

    # 1) string-level 规范化（不跟随 symlink）
    normalized_str = os.path.normpath(str(path)).replace("\\", "/")
    is_windows = (
        len(normalized_str) >= 2 and normalized_str[1] == ":"
    )

    if not is_windows:
        try:
            normalized_posix = Path(normalized_str)
        except (OSError, ValueError):
            normalized_posix = None
        if normalized_posix is not None:
            for ancestor in normalized_posix.parents:
                if _normalize_for_compare(ancestor) in posix_forbidden:
                    return True
            if _normalize_for_compare(normalized_posix) in posix_forbidden:
                return True

    # 2) Path.resolve() 处理 symlink
    try:
        resolved = Path(path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        resolved = None
    if resolved is not None and not is_windows:
        for ancestor in resolved.parents:
            if _normalize_for_compare(ancestor) in posix_forbidden:
                return True
        if _normalize_for_compare(resolved) in posix_forbidden:
            return True

    # 3) Windows 特有检查：盘符 + 路径元组对比
    drive = _windows_drive(path)
    if drive is not None:
        for forbidden in _FORBIDDEN_WINDOWS_DIRS:
            if _windows_path_matches(path, forbidden):
                return True
    return False


def _windows_drive(path: Path) -> str | None:
    """如果路径看起来像 Windows 路径（含盘符），返回小写盘符。"""
    s = str(path)
    if len(s) >= 2 and s[1] == ":":
        return s[0].lower()
    return None


def _windows_path_matches(path: Path, forbidden: str) -> bool:
    """判断 ``path`` 是否位于 Windows ``forbidden`` 目录下。

    ``forbidden`` 形如 ``c:\\windows`` / ``c:\\program files``。仅在
    同盘符情况下匹配，并对路径元素逐级比较。

    实现要点：必须**手动解析路径字符串**，不能依赖
    :py:attr:`Path.parts` —— 在 POSIX 平台下，
    ``Path("c:\\windows\\evil.exe")`` 会被当成单一文件名（parts = 1），
    无法拆分出 ``c:`` / ``windows`` 两段；在 Windows 平台下，
    ``path.parts`` 则是 ``('c:\\', 'windows', 'evil.exe')``。两种情况
    通过字符串级别的 ``split("/")`` 统一处理。
    """
    forbidden_norm = forbidden.replace("\\", "/").strip("/").lower()
    forbidden_parts = forbidden_norm.split("/")
    drive = forbidden_parts[0]  # e.g. "c:"
    if _windows_drive(path) != drive[0]:
        return False

    raw = str(path).replace("\\", "/").lstrip("/")
    parts = [p for p in raw.split("/") if p]
    path_parts_lower = [p.lower() for p in parts]
    if not path_parts_lower or path_parts_lower[0] != drive:
        return False
    return path_parts_lower[: len(forbidden_parts)] == forbidden_parts


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

        Delegates to individual validation methods for each concern.
        """
        self._validate_input_file()
        self._validate_output_path()
        self._validate_codec_params()
        self._validate_quality_params()
        self._validate_audio_params()
        self._validate_filters_and_args()
        self._validate_hwaccel()

    def _validate_input_file(self) -> None:
        """Validate that the input file exists and is a regular file."""
        if not self.input_file.exists():
            raise FFmpegSecurityError(
                f"Input file not found: {self.input_file}")
        if not self.input_file.is_file():
            raise FFmpegSecurityError(
                f"Input is not a file: {self.input_file}")

    def _validate_output_path(self) -> None:
        """校验输出路径安全（避免系统目录、path traversal 与 shell 元字符）。

        Phase 1 · SEC-06 修复要点：

        之前仅用字符串包含判断 (``forbidden in out_str``)，但
        ``Path.absolute()`` *不会*解析 ``..``，攻击者可以传入
        ``"/Users/public/../etc/passwd"`` 等路径绕过检查。修复后：

        1. 先在 *原始（未解析）路径* 上调 ``_is_under_forbidden``，这样 ``/etc/foo``
           （在 macOS 上是 symlink，但逻辑路径仍包含 ``etc`` 段）会被一并拒绝；
        2. 再调用 :py:meth:`Path.resolve(strict=False)` 解析 ``..`` 和 symlink，
           复检避免 symlink 跳转；
        3. 危险字符检测保留，防止后续 shell 拼接。
        """
        # 1) 原始路径预检查（不解析 symlink）
        if _is_under_forbidden(self.output_file):
            raise FFmpegSecurityError(
                f"Output path rejected (forbidden directory): {self.output_file}"
            )

        # 2) 解析（处理 .. 和 symlink）
        try:
            resolved = Path(self.output_file).expanduser().resolve(
                strict=False)
        except (OSError, RuntimeError) as exc:
            raise FFmpegSecurityError(
                f"Cannot resolve output path: {self.output_file} ({exc})"
            )

        if not str(resolved):
            raise FFmpegSecurityError("Output path is empty")
        if not resolved.is_absolute():
            raise FFmpegSecurityError(
                f"Output path must be absolute after resolution: {resolved}"
            )

        # 3) 解析后路径再验一遍（防止 symlink 跳转进受限目录）
        if _is_under_forbidden(resolved):
            raise FFmpegSecurityError(
                f"Output path rejected (forbidden directory): {resolved}"
            )

        # 4) 危险字符检测
        if _DANGEROUS_CHARS.search(str(resolved)):
            raise FFmpegSecurityError(
                f"Output path contains dangerous characters: {resolved}"
            )

        # 5) 用解析后的路径替换原始路径，避免后续绕过
        self.output_file = resolved

    def _validate_codec_params(self) -> None:
        """Validate codec, preset, pixel format, and CRF against whitelists."""
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
            raise FFmpegSecurityError(
                f"Pixel format '{self.pix_fmt}' not in whitelist")
        if not (CRF_RANGE[0] <= self.crf <= CRF_RANGE[1]):
            raise FFmpegSecurityError(
                f"CRF {self.crf} out of range [{CRF_RANGE[0]}, {CRF_RANGE[1]}]"
            )

    def _validate_quality_params(self) -> None:
        """Validate bitrate range when bitrate override is set."""
        if self.bitrate_mbps is not None:
            if not (0.1 <= self.bitrate_mbps <= BITRATE_MAX_MBPS):
                raise FFmpegSecurityError(
                    f"Bitrate {self.bitrate_mbps} Mbps out of range "
                    f"[0.1, {BITRATE_MAX_MBPS}]"
                )

    def _validate_audio_params(self) -> None:
        """Validate audio codec whitelist and bitrate range."""
        if self.audio_codec not in ALLOWED_CODECS:
            raise FFmpegSecurityError(
                f"Audio codec '{self.audio_codec}' not in whitelist"
            )
        if not (32 <= self.audio_bitrate_kbps <= 512):
            raise FFmpegSecurityError(
                f"Audio bitrate {self.audio_bitrate_kbps} kbps out of range [32, 512]"
            )

    def _validate_filters_and_args(self) -> None:
        """Validate that filters and extra_args contain no dangerous characters."""
        for f in self.filters:
            if _DANGEROUS_CHARS.search(f):
                raise FFmpegSecurityError(
                    f"Filter contains dangerous characters: {f!r}"
                )
        for arg in self.extra_args:
            if _DANGEROUS_CHARS.search(arg):
                raise FFmpegSecurityError(
                    f"Extra arg contains dangerous characters: {arg!r}"
                )

    def _validate_hwaccel(self) -> None:
        """Validate hwaccel against the allowed set."""
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
        logger.info(
            f"FFmpeg execute: {' '.join(shlex.quote(c) for c in cmd[:6])}...")

        if audit:
            self._log_execute_start()

        # 统一执行入口：复用全局安全执行器底座（不再各自 subprocess.run）
        from app.utils.security import SecurityError, get_ffmpeg_executor

        try:
            result = get_ffmpeg_executor().run(cmd, timeout=self.timeout_sec)
            return self._build_result(result, cmd, start_ms, audit)
        except SecurityError as e:
            # SecureExecutor 将超时/执行失败统一包装为 SecurityError。
            # 超时单独审计后按原契约重新抛出 TimeoutExpired，其余按执行错误处理。
            if "超时" in str(e):
                self._handle_timeout(start_ms, audit)
                raise subprocess.TimeoutExpired(cmd, self.timeout_sec) from e
            self._handle_execution_error(e, start_ms, audit)
            raise

    def _log_execute_start(self) -> None:
        """Emit the pre-execution audit log entry."""
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

    def _build_result(
        self,
        result: "subprocess.CompletedProcess[str]",
        cmd: list[str],
        start_ms: int,
        audit: bool,
    ) -> FFmpegResult:
        """Compose FFmpegResult from a completed subprocess and audit the outcome."""
        import time

        duration_ms = int(time.time() * 1000) - start_ms
        success = result.returncode == 0

        if audit:
            self._log_execute_done(result, duration_ms, success)

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

    def _log_execute_done(
        self,
        result: "subprocess.CompletedProcess[str]",
        duration_ms: int,
        success: bool,
    ) -> None:
        """Emit the post-execution audit log entry."""
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

    def _handle_timeout(self, start_ms: int, audit: bool) -> None:
        """Log and audit a subprocess timeout before re-raising."""
        import time

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

    def _handle_execution_error(
        self,
        exc: Exception,
        start_ms: int,
        audit: bool,
    ) -> None:
        """Log and audit a generic execution error before re-raising."""
        import time

        duration_ms = int(time.time() * 1000) - start_ms
        logger.error(f"FFmpeg execution failed: {exc}")
        if audit:
            AuditLogger().log_action(
                action="ffmpeg_execute_error",
                parameters={"input": str(self.input_file.absolute())},
                result="failure",
                duration_ms=duration_ms,
                error_message=str(exc),
                error_type=type(exc).__name__,
            )


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

    Phase 1 · SEC-06 修复后改用 :func:`_is_under_forbidden` 逐级
    检查路径，避免 :py:meth:`Path.absolute` 不解析 ``..`` 的问题。

    修复后额外加一道「原始路径预检」：在 :py:meth:`Path.resolve` 之
    前先用原路径调一次 :func:`_is_under_forbidden`，避免 macOS 上
    ``/etc`` 跳转到 ``/private/etc`` 后被放行。
    """

    raw_path = Path(path)

    # 1) 原始路径预检查（不解析 symlink）
    if _is_under_forbidden(raw_path):
        return False

    try:
        p = raw_path.expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        return False

    # 2) 解析后路径再检查
    if _is_under_forbidden(p):
        return False

    p_str = str(p).lower()
    # 危险字符
    if _DANGEROUS_CHARS.search(p_str):
        return False

    # 基础目录限制
    if allowed_bases is not None:
        try:
            resolved_bases = [
                Path(base).expanduser().resolve(strict=False)
                for base in allowed_bases
            ]
            p.relative_to(*resolved_bases)
        except (ValueError, OSError):
            return False

    return True


# ══════════════════════════════════════════════════════════════
# 异步版本（不改变现有 sync API）
# ══════════════════════════════════════════════════════════════


async def execute_async(
    cmd: list[str],
    timeout: float = 30.0,
) -> int:
    """
    异步执行 ffmpeg/ffprobe 命令（非阻塞）。

    Args:
        cmd: 完整命令列表（第一个元素应为 ffmpeg/ffprobe）
        timeout: 超时秒数

    Returns:
        returncode (0 表示成功)
    """
    from app.utils.async_subprocess import run_subprocess

    returncode, _, _ = await run_subprocess(cmd, timeout=timeout)
    return returncode


__all__ = [
    "SafeFFmpegCommand",
    "FFmpegResult",
    "FFmpegSecurityError",
    "is_safe_path",
    "ALLOWED_CODECS",
    "ALLOWED_PRESETS",
    "execute_async",
]
