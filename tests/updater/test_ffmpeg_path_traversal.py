#!/usr/bin/env python3
"""Tests for ffmpeg_safe path-traversal fix (Phase 1 · SEC-06).

Before the fix, :py:meth:`SafeFFmpegCommand._validate_output_path` only used
string contains (``forbidden in out_str``). Because :py:meth:`Path.absolute`
does NOT normalize ``..``, an attacker could supply
``/Users/x/../etc/passwd`` and bypass the directory blacklist.

These tests verify that :

* All obvious path-traversal vectors are now rejected;
* Legitimate outputs (e.g. inside $HOME, /tmp, project subdirs) still pass;
* The fix also covers the public :py:func:`is_safe_path` helper.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


class TestForbiddenSegments:
    @pytest.mark.parametrize(
        "path",
        [
            "/etc/passwd",
            "/etc/cron.d/anything",
            "/bin/sh",
            "/usr/bin/python",
            "/var/log/syslog",
            "/root/.ssh/id_rsa",
            "/dev/null",
            "/proc/cpuinfo",
            "/sys/kernel",
            "/boot/grub/grub.cfg",
        ],
    )
    def test_blocks_sys_dirs(self, tmp_path: Path, path: str):
        from app.core.ffmpeg_safe import _is_under_forbidden

        assert _is_under_forbidden(Path(path)) is True

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only check")
    @pytest.mark.parametrize(
        "path",
        [
            "C:\\Windows\\System32\\evil.exe",
            "C:\\Program Files\\App\\a.dll",
            "C:\\Program Files (x86)\\App\\a.dll",
        ],
    )
    def test_blocks_windows_sys_dirs(self, path: str):
        from app.core.ffmpeg_safe import _is_under_forbidden

        assert _is_under_forbidden(Path(path)) is True


class TestPathTraversal:
    """The original bug — ``Path.absolute`` does not resolve ``..``."""

    @pytest.mark.parametrize(
        "path",
        [
            # Pure POSIX traversal
            "/Users/public/../../../etc/passwd",
            # 3 段 . 才能从 /Users 逸出到根目录
            "/Users/x/y/../../../etc/cron.d/file",
            # Tricky relative segments
            "/usr/../etc/passwd",
            "/etc/./passwd",
            # Up-up-up traversal
            "/a/b/c/../../../../../etc/passwd",
        ],
    )
    def test_rejects_traversal_to_sys_dir(self, path: str):
        from app.core.ffmpeg_safe import _is_under_forbidden

        assert _is_under_forbidden(Path(path)) is True


class TestAllowedPaths:
    @pytest.mark.parametrize(
        "path",
        [
            "/Users/me/Movies/output.mp4",
            "/home/ubuntu/Videos/clip.mkv",
            "/tmp/scenefab/export.mp4",
            "/var/folders/xx/yy/T/output.mp4",
            "/data/projects/abc/final.mp4",
        ],
    )
    def test_allows_normal_user_paths(self, path: str):
        from app.core.ffmpeg_safe import _is_under_forbidden

        assert _is_under_forbidden(Path(path)) is False


class TestIsSafePath:
    """Public helper also blocks traversal."""

    def test_safe_user_path(self, tmp_path: Path):
        from app.core.ffmpeg_safe import is_safe_path

        target = tmp_path / "out.mp4"
        assert is_safe_path(target) is True

    def test_blocks_traversal(self, tmp_path: Path):
        from app.core.ffmpeg_safe import is_safe_path

        # 直接给 /etc/... 是 forbidden —— 应当被拒绝
        assert is_safe_path(Path("/etc/passwd")) is False
        # 带 ``..`` 的绝对路径最终落地在 /etc —— 同样应当被拒绝
        assert is_safe_path(Path("/var/../etc/passwd")) is False
        # 原始逻辑路径中带 ``etc`` 段（macOS symlink 防护）
        assert is_safe_path(Path("/etc/foo/../bar")) is False
        # sanity：tmp_path 下的正常路径应当被接受
        assert is_safe_path(tmp_path / "x/y/../../safe.mp4") is True


class TestSafeFFmpegCommandOutputPath:
    """End-to-end validation through :class:`SafeFFmpegCommand`."""

    def _build(self, output: Path, *, input_file: Path | None = None):
        from app.core.ffmpeg_safe import SafeFFmpegCommand

        if input_file is None:
            input_file = Path("/tmp/in.mp4")
            input_file.write_bytes(b"x")
        return SafeFFmpegCommand(
            input_file=input_file,
            output_file=output,
        )

    def test_accepts_normal_output(self, tmp_path: Path):
        cmd = self._build(tmp_path / "out.mp4")
        cmd.validate()  # should not raise

    def test_rejects_traversal_in_output(self, tmp_path: Path):
        from app.core.ffmpeg_safe import FFmpegSecurityError

        # 使用绝对路径 + ``..``，normpath 之后实际落到 /etc
        bad = Path("/tmp/../etc/evil")
        cmd = self._build(bad)
        with pytest.raises(FFmpegSecurityError):
            cmd.validate()

        # 多重 ``..`` 落到 /usr（同样在 forbidden 列表）
        bad2 = Path("/var/log/../../usr/share/evil")
        cmd2 = self._build(bad2)
        with pytest.raises(FFmpegSecurityError):
            cmd2.validate()

    def test_rejects_cwd_relative_when_resolves_to_forbidden(self, tmp_path: Path):
        """``./x/../..`` style chains still must be rejected."""
        from app.core.ffmpeg_safe import FFmpegSecurityError

        # Construct a path using .. that, even when expanded, hits /etc
        cmd = self._build(Path("/etc/output.mp4"))
        with pytest.raises(FFmpegSecurityError):
            cmd.validate()

    def test_windows_path_resolves_backslashes(self):
        """Backslash separator should be normalized for comparison."""
        from app.core.ffmpeg_safe import _is_under_forbidden

        # ``c:\windows\foo`` is reported as forbidden regardless of separator style
        assert _is_under_forbidden(Path("c:\\windows\\evil.exe")) is True
        assert _is_under_forbidden(Path("c:/windows/evil.exe")) is True
