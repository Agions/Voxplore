#!/usr/bin/env python3
"""
v2.0 核心模块测试 — BaseWorker / Audit / Pipeline / FFmpeg / Batch / ShortDrama / Platform
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# === BaseWorker ===


class TestBaseWorker:
    def test_worker_result_dataclass(self):
        from scenefab.core.base_worker import WorkerResult

        r = WorkerResult(success=True, data="test", duration_ms=100)
        assert r.success
        assert r.data == "test"
        assert r.duration_ms == 100

    def test_base_worker_name(self):
        from scenefab.core.base_worker import BaseWorker

        class TestWorker(BaseWorker):
            def _run(self):
                self.emit_status("running")
                self.emit_progress(50, 100, "half")
                return None

        w = TestWorker(name="TestWorker")
        assert w.get_name() == "TestWorker"
        assert not w.is_cancelled()

    def test_base_worker_cancel(self):
        from scenefab.core.base_worker import BaseWorker

        class TestWorker(BaseWorker):
            def _run(self):
                if self.check_cancel_or_pause():
                    return
                self.emit_status("after cancel check")

        w = TestWorker()
        w.cancel()
        assert w.is_cancelled()

    def test_base_worker_pause_resume(self):
        from scenefab.core.base_worker import BaseWorker

        class TestWorker(BaseWorker):
            def _run(self):
                self.pause()
                assert self.is_paused()
                self.resume()
                assert not self.is_paused()

        w = TestWorker()
        w.run()  # 同步测试（run → _execute → _run）


# === AuditLogger ===


class TestAuditLogger:
    def test_log_entry(self):
        from scenefab.core.audit import AuditLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_audit.db"
            logger = AuditLogger(db_path=db_path)
            logger.log_action(
                action="test_action",
                parameters={"key": "value"},
                result="success",
                duration_ms=100,
            )
            count = logger.count(action="test_action")
            assert count == 1

    def test_log_failure(self):
        from scenefab.core.audit import AuditLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_audit.db"
            logger = AuditLogger(db_path=db_path)
            logger.log_action(
                action="test_fail",
                parameters={},
                result="failure",
                error_message="Test error",
                error_type="ValueError",
            )
            entries = logger.query(action="test_fail")
            assert len(entries) == 1
            assert entries[0].error_message == "Test error"
            assert entries[0].error_type == "ValueError"

    def test_track_context_manager(self):
        from scenefab.core.audit import AuditLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_audit.db"
            logger = AuditLogger(db_path=db_path)
            with logger.track("test_track", {"x": 1}) as ctx:
                ctx["extra"]["computed"] = 42
            entries = logger.query(action="test_track")
            assert len(entries) == 1
            assert entries[0].parameters.get("computed") == 42

    def test_track_exception(self):
        from scenefab.core.audit import AuditLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_audit.db"
            logger = AuditLogger(db_path=db_path)
            with pytest.raises(ValueError), logger.track("test_exc", {}):
                raise ValueError("test error")
            entries = logger.query(action="test_exc", result="failure")
            assert len(entries) == 1
            assert "test error" in entries[0].error_message


# === SafeFFmpegCommand ===


class TestSafeFFmpegCommand:
    def test_basic_build(self):
        from scenefab.core.ffmpeg_safe import SafeFFmpegCommand

        # 创建临时输入文件
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake")
            input_path = Path(f.name)

        try:
            cmd = SafeFFmpegCommand(
                input_file=input_path,
                output_file=Path("/tmp/test_output.mp4"),
                codec="libx264",
            )
            cmd_list = cmd.build()
            assert "ffmpeg" in cmd_list
            assert "-c:v" in cmd_list
            assert "libx264" in cmd_list
            assert "-y" in cmd_list
        finally:
            input_path.unlink()

    def test_codec_whitelist(self):
        from scenefab.core.ffmpeg_safe import FFmpegSecurityError, SafeFFmpegCommand

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            input_path = Path(f.name)

        try:
            cmd = SafeFFmpegCommand(
                input_file=input_path,
                output_file=Path("/tmp/test.mp4"),
                codec="malicious_codec",
            )
            with pytest.raises(FFmpegSecurityError, match="not in whitelist"):
                cmd.build()
        finally:
            input_path.unlink()

    def test_dangerous_chars_in_filter(self):
        from scenefab.core.ffmpeg_safe import FFmpegSecurityError, SafeFFmpegCommand

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            input_path = Path(f.name)

        try:
            cmd = SafeFFmpegCommand(
                input_file=input_path,
                output_file=Path("/tmp/test.mp4"),
                filters=["drawtext=text='hello; rm -rf /'"],
            )
            with pytest.raises(FFmpegSecurityError, match="dangerous characters"):
                cmd.build()
        finally:
            input_path.unlink()

    def test_crf_out_of_range(self):
        from scenefab.core.ffmpeg_safe import FFmpegSecurityError, SafeFFmpegCommand

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            input_path = Path(f.name)

        try:
            cmd = SafeFFmpegCommand(
                input_file=input_path,
                output_file=Path("/tmp/test.mp4"),
                crf=100,
            )
            with pytest.raises(FFmpegSecurityError, match="out of range"):
                cmd.build()
        finally:
            input_path.unlink()

    def test_forbidden_output_path(self):
        from scenefab.core.ffmpeg_safe import FFmpegSecurityError, SafeFFmpegCommand

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            input_path = Path(f.name)

        try:
            cmd = SafeFFmpegCommand(
                input_file=input_path,
                output_file=Path("/etc/passwd"),
            )
            with pytest.raises(FFmpegSecurityError, match="forbidden"):
                cmd.build()
        finally:
            input_path.unlink()

    def test_execute_routes_through_secure_executor(self):
        """execute() 委托统一安全执行器（不再自带 subprocess.run）。"""
        import subprocess

        from scenefab.core.ffmpeg_safe import FFmpegResult, SafeFFmpegCommand

        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / "in.mp4"
            inp.write_bytes(b"x")
            out = Path(d) / "out.mp4"

            def mk():
                return SafeFFmpegCommand(
                    input_file=inp, output_file=out, timeout_sec=600
                )

            # 成功：经 SecureExecutor.run 返回 CompletedProcess → FFmpegResult
            cp = subprocess.CompletedProcess(["ffmpeg"], 0, "ok", "")
            with patch(
                "scenefab.utils.security.SecureExecutor.run", return_value=cp
            ) as m:
                r = mk().execute(audit=False)
                assert isinstance(r, FFmpegResult) and r.success
                assert m.called and isinstance(m.call_args[0][0], list)

            # 非零返回码 → FFmpegResult(success=False)，不抛
            cp_fail = subprocess.CompletedProcess(["ffmpeg"], 1, "", "boom")
            with patch(
                "scenefab.utils.security.SecureExecutor.run", return_value=cp_fail
            ):
                r2 = mk().execute(audit=False)
                assert not r2.success and r2.returncode == 1

            # 超时（SecureExecutor 抛 SecurityError"超时"）→ 按原契约重抛 TimeoutExpired
            from scenefab.utils.security import SecurityError

            with patch(
                "scenefab.utils.security.SecureExecutor.run",
                side_effect=SecurityError("命令执行超时: 600秒"),
            ):
                with pytest.raises(subprocess.TimeoutExpired):
                    mk().execute(audit=False)

    def test_is_safe_path(self):
        from scenefab.core.ffmpeg_safe import is_safe_path

        assert is_safe_path("/tmp/test.mp4")
        assert is_safe_path("/home/user/video.mp4")
        assert not is_safe_path("/etc/passwd")
        assert not is_safe_path("/usr/bin/malicious")


# === ShortDrama ===


class TestShortDrama:
    def test_preset_suspense(self):
        from scenefab.pipeline.short_drama import ShortDramaPreset, ShortDramaStyle

        p = ShortDramaPreset.suspense()
        assert p.style == ShortDramaStyle.SUSPENSE
        assert "悬疑" in p.name

    def test_trope_detection(self):
        from scenefab.pipeline.short_drama import (
            ShortDramaNarrator,
            ShortDramaPreset,
            TropeType,
        )

        narrator = ShortDramaNarrator(preset=ShortDramaPreset.suspense())

        assert (
            narrator.detect_trope("主角的真实身份曝光了") == TropeType.IDENTITY_REVEAL
        )
        assert narrator.detect_trope("狠狠打脸反派") == TropeType.FACE_SLAP
        assert narrator.detect_trope("男主突然出现救了她") == TropeType.RESCUE
        assert narrator.detect_trope("普通场景") == TropeType.GENERAL

    def test_episode_scanning(self):
        from scenefab.pipeline.short_drama import ShortDramaNarrator, ShortDramaPreset

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "series_EP01.mp4").write_bytes(b"fake")
            (tmpdir / "series_EP02.mp4").write_bytes(b"fake")
            (tmpdir / "series_EP10.mp4").write_bytes(b"fake")

            narrator = ShortDramaNarrator(preset=ShortDramaPreset.suspense())
            episodes = narrator.scan_episodes(tmpdir)
            assert len(episodes) == 3
            assert episodes[0].episode_number == 1
            assert episodes[2].episode_number == 10

    def test_chinese_episode_pattern(self):
        from scenefab.pipeline.short_drama import ShortDramaNarrator, ShortDramaPreset

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "重生女王_第01集.mp4").write_bytes(b"fake")
            (tmpdir / "重生女王_第15集.mp4").write_bytes(b"fake")

            narrator = ShortDramaNarrator(preset=ShortDramaPreset.suspense())
            episodes = narrator.scan_episodes(tmpdir)
            assert len(episodes) == 2
            assert episodes[0].episode_number == 1
            assert episodes[1].episode_number == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
