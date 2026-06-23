#!/usr/bin/env python3
"""
v2.0 核心模块测试 — BaseWorker / Audit / Pipeline / FFmpeg / Batch / ShortDrama / Platform
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

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
            def run(self):
                self.emit_status("running")
                self.emit_progress(50, 100, "half")
                return None

        w = TestWorker(name="TestWorker")
        assert w.get_name() == "TestWorker"
        assert not w.is_cancelled()

    def test_base_worker_cancel(self):
        from scenefab.core.base_worker import BaseWorker

        class TestWorker(BaseWorker):
            def run(self):
                if self.check_cancel_or_pause():
                    return
                self.emit_status("after cancel check")

        w = TestWorker()
        w.cancel()
        assert w.is_cancelled()

    def test_base_worker_pause_resume(self):
        from scenefab.core.base_worker import BaseWorker

        class TestWorker(BaseWorker):
            def run(self):
                self.pause()
                assert self.is_paused()
                self.resume()
                assert not self.is_paused()

        w = TestWorker()
        w.run()  # 同步测试


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


# === PipelineEngine (DAG) ===


class TestPipelineEngine:
    def test_simple_pipeline(self):
        from scenefab.core.pipeline_engine import PipelineEngine, PipelineStep

        engine = PipelineEngine(max_workers=2)
        results_holder = {}

        def step_a(ctx):
            results_holder["a"] = "a_result"
            return "a_out"

        def step_b(ctx):
            results_holder["b"] = "b_result"
            return "b_out"

        engine.add_step(PipelineStep(id="a", func=step_a))
        engine.add_step(PipelineStep(id="b", func=step_b, dependencies=["a"]))

        result = engine.run({})
        assert "a" in result["steps"]
        assert "b" in result["steps"]
        assert results_holder["a"] == "a_result"
        assert results_holder["b"] == "b_result"

    def test_parallel_pipeline(self):
        from scenefab.core.pipeline_engine import PipelineEngine, PipelineStep

        engine = PipelineEngine(max_workers=4)
        timings = {}

        def slow_step(name, duration):
            def _step(ctx):
                start = time.time()
                time.sleep(duration)
                timings[name] = time.time() - start
                return name

            return _step

        engine.add_step(PipelineStep(id="base", func=slow_step("base", 0.1)))
        engine.add_step(
            PipelineStep(
                id="branch_a",
                func=slow_step("branch_a", 0.2),
                dependencies=["base"],
                parallel_group="group1",
            )
        )
        engine.add_step(
            PipelineStep(
                id="branch_b",
                func=slow_step("branch_b", 0.2),
                dependencies=["base"],
                parallel_group="group1",
            )
        )
        engine.add_step(
            PipelineStep(
                id="final",
                func=slow_step("final", 0.1),
                dependencies=["branch_a", "branch_b"],
            )
        )

        start = time.time()
        result = engine.run({})
        total = time.time() - start

        # 串行需要 0.6s (0.1+0.2+0.2+0.1)，并行应 < 0.55s（允许调度开销）
        assert total < 0.55, f"Parallel pipeline too slow: {total}s"
        assert "final" in result["steps"]

    def test_circular_dependency_detection(self):
        from scenefab.core.pipeline_engine import PipelineEngine, PipelineStep

        engine = PipelineEngine()
        engine.add_step(PipelineStep(id="a", func=lambda c: None, dependencies=["b"]))
        engine.add_step(PipelineStep(id="b", func=lambda c: None, dependencies=["a"]))

        with pytest.raises(ValueError, match="Circular dependency"):
            engine.run({})

    def test_unknown_dependency(self):
        from scenefab.core.pipeline_engine import PipelineEngine, PipelineStep

        engine = PipelineEngine()
        engine.add_step(
            PipelineStep(id="a", func=lambda c: None, dependencies=["nonexistent"])
        )
        with pytest.raises(ValueError, match="unknown dependency"):
            engine.run({})

    def test_skip_on_failure(self):
        from scenefab.core.pipeline_engine import PipelineEngine, PipelineStep

        engine = PipelineEngine(fail_fast=True)

        def fail_func(ctx):
            raise RuntimeError("intentional")

        def should_skip(ctx):
            raise AssertionError("should not be called")

        engine.add_step(PipelineStep(id="fail", func=fail_func))
        engine.add_step(
            PipelineStep(id="after", func=should_skip, dependencies=["fail"])
        )

        engine.run({})
        summary = engine.summary()
        assert summary["failed"] == 1
        assert summary["skipped"] == 1

    def test_always_run_step(self):
        from scenefab.core.pipeline_engine import (
            PipelineEngine,
            PipelineStep,
            StepStatus,
        )

        engine = PipelineEngine(fail_fast=True)
        cleanup_ran = []

        def fail_func(ctx):
            raise RuntimeError("intentional")

        def cleanup(ctx):
            cleanup_ran.append(True)

        engine.add_step(PipelineStep(id="fail", func=fail_func))
        engine.add_step(
            PipelineStep(
                id="cleanup",
                func=cleanup,
                dependencies=["fail"],
                always_run=True,
            )
        )

        # 拦截 audit 调用，专注于行为验证
        with patch("scenefab.core.pipeline_engine.AuditLogger") as mock_audit_cls:
            mock_audit = MagicMock()
            mock_audit_cls.return_value = mock_audit
            engine.run({})

        assert cleanup_ran == [True]
        # 验证 fail 步骤被标记为 FAILED
        assert engine.get_state("fail") == StepStatus.FAILED
        # 验证 cleanup 步骤被标记为 COMPLETED
        assert engine.get_state("cleanup") == StepStatus.COMPLETED

    def test_step_receives_immutable_steps_snapshot(self):
        """step 收到只读 steps 快照：可读已完成依赖结果，写入抛错。"""
        from scenefab.core.pipeline_engine import PipelineEngine, PipelineStep

        engine = PipelineEngine(max_workers=2)
        captured = {}

        def upstream(ctx):
            return "up_value"

        def downstream(ctx):
            # 可读到已完成依赖的结果
            captured["dep"] = ctx["steps"]["up"]
            # 写只读快照应抛 TypeError（MappingProxyType）
            try:
                ctx["steps"]["x"] = 1
                captured["write_blocked"] = False
            except TypeError:
                captured["write_blocked"] = True
            return "down_value"

        engine.add_step(PipelineStep(id="up", func=upstream))
        engine.add_step(
            PipelineStep(id="down", func=downstream, dependencies=["up"])
        )

        result = engine.run({})

        assert captured["dep"] == "up_value"  # 中央归并的依赖结果可读
        assert captured["write_blocked"] is True  # 只读快照禁止写
        # 公开输出契约不变
        assert result["steps"]["up"] == "up_value"
        assert result["steps"]["down"] == "down_value"
        # step 写 ctx["steps"] 未污染权威结果
        assert "x" not in result["steps"]


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


# === BatchProcessor ===


class TestBatchProcessor:
    def test_simple_batch(self):
        from scenefab.core.batch_processor import (
            BatchConfig,
            BatchProcessor,
            BatchTask,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            # 创建 fake 视频文件
            tasks = []
            for i in range(3):
                vp = tmpdir / f"ep{i:02d}.mp4"
                vp.write_bytes(b"fake")
                tasks.append(
                    BatchTask(
                        id=f"ep{i:02d}",
                        video_path=vp,
                        output_dir=tmpdir / "out",
                    )
                )

            # Mock pipeline
            class MockPipeline:
                def __init__(self, task):
                    self.task = task

                def run(self, **kwargs):
                    output = self.task.output_dir / f"{self.task.id}.mp4"
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"result")
                    return str(output)

            config = BatchConfig(tasks=tasks, parallel_count=2)
            processor = BatchProcessor(config, pipeline_factory=MockPipeline)
            processor.start()
            processor.wait_until_done(timeout=10)

            summary = processor.summary()
            assert summary["by_status"]["completed"] == 3

    def test_batch_retry_on_failure(self):
        from scenefab.core.batch_processor import (
            BatchConfig,
            BatchProcessor,
            BatchTask,
            BatchTaskStatus,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            vp = tmpdir / "ep.mp4"
            vp.write_bytes(b"fake")
            tasks = [BatchTask(id="ep01", video_path=vp, output_dir=tmpdir / "out")]

            attempt_count = [0]

            class FlakeyPipeline:
                def __init__(self, task):
                    self.task = task

                def run(self, **kwargs):
                    attempt_count[0] += 1
                    if attempt_count[0] < 2:
                        raise RuntimeError("flakey failure")
                    output = self.task.output_dir / f"{self.task.id}.mp4"
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"ok")
                    return str(output)

            config = BatchConfig(tasks=tasks, parallel_count=1, max_retries=2)
            processor = BatchProcessor(config, pipeline_factory=FlakeyPipeline)
            processor.start()
            processor.wait_until_done(timeout=15)

            assert attempt_count[0] == 2
            assert tasks[0].status == BatchTaskStatus.COMPLETED

    def test_checkpoint_resume(self):
        from scenefab.core.batch_processor import (
            BatchConfig,
            BatchProcessor,
            BatchTask,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            cp_path = tmpdir / "checkpoint.db"
            tasks = [
                BatchTask(
                    id="ep01",
                    video_path=tmpdir / "ep.mp4",
                    output_dir=tmpdir / "out",
                )
            ]
            (tmpdir / "ep.mp4").write_bytes(b"fake")

            # 第一次跑
            class MockPipeline:
                def __init__(self, task):
                    self.task = task

                def run(self, **kwargs):
                    output = self.task.output_dir / f"{self.task.id}.mp4"
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"ok")
                    return str(output)

            config = BatchConfig(
                tasks=tasks,
                parallel_count=1,
                checkpoint_path=cp_path,
            )
            processor = BatchProcessor(config, pipeline_factory=MockPipeline)
            processor.start()
            processor.wait_until_done(timeout=10)
            assert tasks[0].status.value == "completed"

            # 第二次跑（应从断点恢复，不重复处理）
            tasks2 = [
                BatchTask(
                    id="ep01",
                    video_path=tmpdir / "ep.mp4",
                    output_dir=tmpdir / "out",
                )
            ]
            config2 = BatchConfig(
                tasks=tasks2,
                parallel_count=1,
                checkpoint_path=cp_path,
            )
            BatchProcessor(config2, pipeline_factory=MockPipeline)
            assert tasks2[0].status.value == "completed"  # 已恢复

    def test_batch_task_timeout(self):
        """task_timeout_sec 触发超时 → 任务标记 FAILED（不挂死 worker）。"""
        import time as _t

        from scenefab.core.batch_processor import (
            BatchConfig,
            BatchProcessor,
            BatchTask,
            BatchTaskStatus,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            vp = tmpdir / "ep.mp4"
            vp.write_bytes(b"fake")
            tasks = [BatchTask(id="slow", video_path=vp, output_dir=tmpdir / "out")]

            class SlowPipeline:
                def __init__(self, task):
                    self.task = task

                def run(self, **kwargs):
                    _t.sleep(5)  # 远超 timeout
                    return None

            # 1s 超时, 不重试
            config = BatchConfig(
                tasks=tasks,
                parallel_count=1,
                auto_retry=False,
                task_timeout_sec=1,
            )
            processor = BatchProcessor(config, pipeline_factory=SlowPipeline)
            start = _t.time()
            processor.start()
            processor.wait_until_done(timeout=10)
            elapsed = _t.time() - start

            assert tasks[0].status == BatchTaskStatus.FAILED
            assert elapsed < 5, f"timeout not enforced, took {elapsed}s"


# === ShortDrama ===


class TestShortDrama:
    def test_preset_suspense(self):
        from scenefab.core.short_drama import ShortDramaPreset, ShortDramaStyle

        p = ShortDramaPreset.suspense()
        assert p.style == ShortDramaStyle.SUSPENSE
        assert "悬疑" in p.name

    def test_trope_detection(self):
        from scenefab.core.short_drama import (
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
        from scenefab.core.short_drama import ShortDramaNarrator, ShortDramaPreset

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
        from scenefab.core.short_drama import ShortDramaNarrator, ShortDramaPreset

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "重生女王_第01集.mp4").write_bytes(b"fake")
            (tmpdir / "重生女王_第15集.mp4").write_bytes(b"fake")

            narrator = ShortDramaNarrator(preset=ShortDramaPreset.suspense())
            episodes = narrator.scan_episodes(tmpdir)
            assert len(episodes) == 2
            assert episodes[0].episode_number == 1
            assert episodes[1].episode_number == 15


# === Platform Adapter ===


class TestPlatformAdapter:
    def test_platform_configs_exist(self):
        from scenefab.core.platform_adapter import PLATFORM_CONFIGS, Platform

        assert Platform.DOUYIN in PLATFORM_CONFIGS
        assert Platform.BILIBILI in PLATFORM_CONFIGS
        assert Platform.XIAOHONGSHU in PLATFORM_CONFIGS

    def test_douyin_is_vertical(self):
        from scenefab.core.platform_adapter import PLATFORM_CONFIGS, Platform

        cfg = PLATFORM_CONFIGS[Platform.DOUYIN]
        assert cfg.aspect_ratio == "9:16"
        assert cfg.resolution[0] < cfg.resolution[1]  # 竖屏
        assert cfg.supports_vertical

    def test_bilibili_is_horizontal(self):
        from scenefab.core.platform_adapter import PLATFORM_CONFIGS, Platform

        cfg = PLATFORM_CONFIGS[Platform.BILIBILI]
        assert cfg.aspect_ratio == "16:9"
        assert cfg.resolution[0] > cfg.resolution[1]
        assert not cfg.supports_vertical

    def test_smart_cropper_16_9_to_9_16(self):
        from scenefab.core.platform_adapter import SmartCropper

        # 直接用 stub 替代，避免依赖 cv2 真实存在
        class StubCap:
            def __init__(self, w, h):
                self._w, self._h = w, h

            def get(self, prop):
                # cv2.CAP_PROP_FRAME_WIDTH=3, CAP_PROP_FRAME_HEIGHT=4
                if prop == 3:
                    return float(self._w)
                if prop == 4:
                    return float(self._h)
                return 0

            def release(self):
                pass

        cropper = SmartCropper()
        # 通过 sys.modules 注入假 cv2
        import sys
        from types import ModuleType

        fake_cv2 = ModuleType("cv2")
        fake_cv2.CAP_PROP_FRAME_WIDTH = 3
        fake_cv2.CAP_PROP_FRAME_HEIGHT = 4
        fake_cv2.VideoCapture = lambda *a, **kw: StubCap(1920, 1080)
        sys.modules["cv2"] = fake_cv2

        try:
            crop = cropper.auto_crop(Path("fake.mp4"), "9:16", sample_count=1)
            # 1920x1080 → 9:16 需裁宽，等比后 1080*9/16 = 607.5
            assert crop.width == 607
            assert crop.height == 1080
        finally:
            sys.modules.pop("cv2", None)

    def test_crop_to_ffmpeg_filter(self):
        from scenefab.core.platform_adapter import CropRegion

        crop = CropRegion(x=100, y=50, width=800, height=600)
        assert crop.to_ffmpeg_filter() == "crop=800:600:100:50"


# === 集成测试 ===


class TestIntegration:
    def test_audit_during_pipeline(self):
        """Pipeline 执行的每步都应记录到审计日志"""
        from scenefab.core.audit import AuditLogger
        from scenefab.core.pipeline_engine import PipelineEngine, PipelineStep

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "audit.db"
            audit = AuditLogger(db_path=db_path)

            engine = PipelineEngine(max_workers=1)
            engine.add_step(PipelineStep(id="step1", func=lambda c: "result1"))
            engine.add_step(
                PipelineStep(
                    id="step2",
                    func=lambda c: "result2",
                    dependencies=["step1"],
                )
            )

            engine.run({})

            # 应有 pipeline_run + 2 step records
            assert audit.count(action="pipeline_run") >= 1
            assert audit.count(action="pipeline_step_start") >= 2
            assert audit.count(action="pipeline_step_done") >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
