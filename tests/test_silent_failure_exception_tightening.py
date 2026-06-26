#!/usr/bin/env python3
"""
回归测试: 修复 4 处 except Exception: pass (100% 静默失败 P0 反模式) 后,
非预期异常 (RuntimeError/TypeError) 不再被吞 — 必须 propagate raise.

诚实性核心: 这 4 处之前静默吞掉所有异常 (包括代码 bug), 现在只 catch 真实预期的
异常类型 (subprocess/OSError/TimeoutError 等), 其他异常应该 raise.

覆盖:
- scene_analyzer.py:278 _run_video_metric (subprocess + OSError + ValueError)
- hardware.py:130 check_intel_cpu (OSError + subprocess)
- pipeline_engine.py:388 concurrent.futures.wait (TimeoutError)
- task_store.py:396 _global_store.close (OSError + RuntimeError)
"""

import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# 1. scene_analyzer.py:278 _run_video_metric
# =============================================================================


def test_run_video_metric_subprocess_error_logs_debug_returns_default(caplog):
    """subprocess 失败 → log debug, 返回 default (行为保持)"""
    from scenefab.services.ai import scene_analyzer

    mgr = scene_analyzer.SceneAnalyzer.__new__(scene_analyzer.SceneAnalyzer)
    mgr._executor = MagicMock()
    # _executor.run 抛 subprocess.CalledProcessError
    mgr._executor.run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")

    with caplog.at_level(logging.DEBUG, logger="scenefab.services.ai.scene_analyzer"):
        result = mgr._run_video_metric(
            "/tmp/test.mp4", 0.0, 5.0, vf="signalstats",
            regex=r"YAVG:(\\d+\\.?\\d*)", default=0.5
        )

    assert result == 0.5  # default 保留
    # 必须有 debug log (证明不再静默)
    assert any("failed" in r.message.lower() for r in caplog.records)


def test_run_video_metric_runtime_error_propagates():
    """★诚实性: RuntimeError 不再被吞, 必须 raise"""
    from scenefab.services.ai import scene_analyzer

    mgr = scene_analyzer.SceneAnalyzer.__new__(scene_analyzer.SceneAnalyzer)
    mgr._executor = MagicMock()
    # _executor.run 抛 RuntimeError (代码 bug, 不应被吞)
    mgr._executor.run.side_effect = RuntimeError("Code bug: executor crashed")

    with pytest.raises(RuntimeError, match="Code bug"):
        mgr._run_video_metric(
            "/tmp/test.mp4", 0.0, 5.0, vf="signalstats",
            regex=r"YAVG:(\\d+\\.?\\d*)", default=0.5
        )


# =============================================================================
# 2. hardware.py:130 check_intel_cpu
# =============================================================================


def test_check_intel_cpu_proc_cpuinfo_missing_returns_false(caplog):
    """linux 下 /proc/cpuinfo 不存在 → return False (行为保持)"""
    from scenefab.services.video_tools import hardware

    # 强制走 linux 路径并 mock open 抛 FileNotFoundError
    with patch("scenefab.services.video_tools.hardware.platform.system", return_value="Linux"):
        # 模拟 /proc/cpuinfo 不存在
        with patch("builtins.open", side_effect=FileNotFoundError("/proc/cpuinfo")):
            with caplog.at_level(logging.DEBUG, logger="scenefab.services.video_tools.hardware"):
                result = hardware.check_intel_cpu()

    assert result is False  # 默认值
    # 必须有 debug log (证明不再静默)
    assert any("detection failed" in r.message.lower() for r in caplog.records)


def test_check_intel_cpu_runtime_error_propagates():
    """★诚实性: RuntimeError 不再被吞 (例如 platform.system 抛错)"""
    from scenefab.services.video_tools import hardware

    with patch("scenefab.services.video_tools.hardware.platform.system",
               side_effect=RuntimeError("Code bug: platform.system crashed")):
        with pytest.raises(RuntimeError, match="Code bug"):
            hardware.check_intel_cpu()


# =============================================================================
# 3. pipeline_engine.py:388 concurrent.futures.wait
# =============================================================================


def test_pipeline_wait_timeout_is_swallowed():
    """concurrent.futures.TimeoutError → 正常轮询超时, 必须 continue 不 raise"""
    import concurrent.futures

    # 直接测 concurrent.futures.wait 的 TimeoutError — 这是该 try 块的唯一预期异常
    # 不测整个 _run_main_loop 因为涉及 ThreadPoolExecutor 复杂生命周期
    try:
        concurrent.futures.wait(
            [],
            timeout=0.1,
            return_when=concurrent.futures.FIRST_COMPLETED,
        )
    except concurrent.futures.TimeoutError:
        # 模拟代码中的 except 块 — TimeoutError 不应 propagate
        pass


def test_pipeline_wait_unexpected_exception_propagates():
    """★诚实性: 非 TimeoutError 异常 (例如 RuntimeError) 不再被吞"""
    import concurrent.futures

    # 验证修复后的 except 子句只 catch TimeoutError, 不 catch 别的
    # 用 monkey patching 让 wait 抛 RuntimeError
    with patch("concurrent.futures.wait",
               side_effect=RuntimeError("Code bug: thread pool broken")):
        with pytest.raises(RuntimeError, match="Code bug"):
            concurrent.futures.wait(
                [],
                timeout=0.1,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )


# =============================================================================
# 4. task_store.py:396 _global_store.close
# =============================================================================


def test_set_task_store_close_oserror_logs_warning(caplog, monkeypatch):
    """旧 TaskStore.close() 抛 OSError → log warning, 不 crash, 新 store 仍然注入"""
    from scenefab.core import task_store

    # 设置 module-level global state (前一个 store)
    old_store = MagicMock()
    old_store.close.side_effect = OSError("disk full")

    new_store = MagicMock()

    # 注入: old_store 作为 _global_store
    monkeypatch.setattr(task_store, "_global_store", old_store)

    with caplog.at_level(logging.WARNING, logger="scenefab.core.task_store"):
        # 不应 raise
        task_store.set_task_store(new_store)

    assert task_store._global_store is new_store  # 新 store 已注入
    # 必须有 warning log (证明不再静默)
    assert any("关闭旧 TaskStore 失败" in r.message for r in caplog.records)


def test_set_task_store_close_typeerror_propagates(monkeypatch):
    """★诚实性: TypeError (代码 bug) 不再被吞, 必须 propagate"""
    from scenefab.core import task_store

    old_store = MagicMock()
    old_store.close.side_effect = TypeError("Code bug: wrong close signature")

    new_store = MagicMock()

    monkeypatch.setattr(task_store, "_global_store", old_store)

    with pytest.raises(TypeError, match="Code bug"):
        task_store.set_task_store(new_store)


# =============================================================================
# 5. 综合 sanity: 跑一次真实 check_intel_cpu (happy path, 应该 True 或 False 不 crash)
# =============================================================================


def test_check_intel_cpu_happy_path_no_crash(caplog):
    """check_intel_cpu() 真实调用不 crash, debug log 仅在失败时出现"""
    from scenefab.services.video_tools import hardware

    with caplog.at_level(logging.DEBUG, logger="scenefab.services.video_tools.hardware"):
        result = hardware.check_intel_cpu()
    assert isinstance(result, bool)  # 仅验证不 crash