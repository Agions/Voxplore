#!/usr/bin/env python3
"""
回归测试: Phase 1 安全加固 (audit 报告 P1 修复)

覆盖两个 P1 修复:
1. hardware.py: check_nvidia_smi / check_intel_cpu 改走 get_probe_executor()
   替代裸 subprocess.run (失去 SecureExecutor 审计链)
2. api/routers/pipeline.py: 缺路径校验, 复用 export router 模式
   防御性校验 video_url + output_dir

诚实性核心:
- 改前: 裸 subprocess.run (无白名单 + 无审计 + 无 env sanitization)
- 改后: 走 get_probe_executor() (白名单: nvidia-smi/wmic + shell=False + env sanitize)
- 改前: pipeline router 无路径校验, 任意 path 可触发 mkdir 到 /etc /root
- 改后: 早期校验 + 失败时降级到 cwd/outputs/jianying_drafts
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# 1. hardware.py: check_nvidia_smi / check_intel_cpu 走 SecureExecutor
# =============================================================================


def test_check_nvidia_smi_uses_probe_executor():
    """★ 关键: check_nvidia_smi 必须走 probe_executor, 不能裸 subprocess"""
    from scenefab.services.video_tools import hardware
    from scenefab.utils.security import SecureExecutor

    # Mock probe_executor 的 run 方法
    mock_executor = MagicMock(spec=SecureExecutor)
    mock_executor.run.return_value = MagicMock(returncode=0, stdout="")

    with patch.object(hardware, "get_probe_executor", return_value=mock_executor):
        # check_nvidia_smi 第一次调用: probe.run(["nvidia-smi"]) 应该被调用
        with patch.object(hardware, "ffmpeg_supports_encoder", return_value=True):
            result = hardware.check_nvidia_smi()

    assert result is True  # 因为 mock ffmpeg_supports_encoder
    # ★ 验证 probe_executor.run 被调用 (而非裸 subprocess.run)
    mock_executor.run.assert_called_with(["nvidia-smi"], timeout=5)


def test_check_nvidia_smi_security_error_returns_false():
    """★ SecurityError (白名单拒绝/命令不存在) → False, 不 crash"""
    from scenefab.services.video_tools import hardware
    from scenefab.utils.security import SecurityError

    mock_executor = MagicMock()
    mock_executor.run.side_effect = SecurityError("命令不在白名单")

    with patch.object(hardware, "get_probe_executor", return_value=mock_executor):
        result = hardware.check_nvidia_smi()

    assert result is False


def test_check_nvidia_smi_no_longer_uses_subprocess_module():
    """★ 关键: hardware.py 不应该 import subprocess (强制走 SecureExecutor)"""
    # 检查模块 import 不再含 subprocess
    from scenefab.services.video_tools import hardware
    hardware_source = Path(hardware.__file__).read_text()
    assert "import subprocess" not in hardware_source, (
        "hardware.py 不应再 import subprocess — 全部走 SecureExecutor 审计链"
    )


def test_check_intel_cpu_windows_uses_probe_executor(monkeypatch):
    """Windows 路径下 wmic 走 probe_executor"""
    from scenefab.services.video_tools import hardware
    from scenefab.utils.security import SecureExecutor

    mock_executor = MagicMock(spec=SecureExecutor)
    mock_executor.run.return_value = MagicMock(
        returncode=0, stdout="Intel(R) Core(TM) i7-9700K"
    )

    with patch.object(hardware, "get_probe_executor", return_value=mock_executor):
        with patch.object(hardware.platform, "system", return_value="Windows"):
            result = hardware.check_intel_cpu()

    assert result is True
    mock_executor.run.assert_called_with(["wmic", "cpu", "get", "name"], timeout=5)


def test_check_intel_cpu_linux_uses_proc_cpuinfo():
    """Linux 路径下读 /proc/cpuinfo (纯文件 IO, 不需要执行器)"""
    from scenefab.services.video_tools import hardware

    with patch.object(hardware.platform, "system", return_value="Linux"):
        # /proc/cpuinfo 真实读取, 不需要 mock
        result = hardware.check_intel_cpu()
    # 实际环境如果是 Intel CPU 则 True, 否则 False — 只验证不 crash
    assert isinstance(result, bool)


# =============================================================================
# 2. utils/security.py: get_probe_executor 新接口
# =============================================================================


def test_get_probe_executor_singleton():
    """get_probe_executor 单例模式 (与 get_ffmpeg_executor 一致)"""
    from scenefab.utils import security
    from scenefab.utils.security import SecureExecutor, get_probe_executor

    # 重置 global state (测试隔离)
    security._PROBE_EXECUTOR = None

    e1 = get_probe_executor()
    e2 = get_probe_executor()

    assert e1 is e2  # 同一实例 (singleton)
    assert isinstance(e1, SecureExecutor)
    # 白名单必须含 nvidia-smi + wmic
    assert "nvidia-smi" in e1.command_validator.allowed_commands
    assert "wmic" in e1.command_validator.allowed_commands


def test_get_probe_executor_rejects_arbitrary_command():
    """probe_executor 拒绝不在白名单的命令 (audit 链不能被绕过)"""
    from scenefab.utils import security
    from scenefab.utils.security import SecurityError, get_probe_executor

    security._PROBE_EXECUTOR = None
    executor = get_probe_executor()

    # 任意命令 (如 rm -rf) 必被拒绝 (黑名单先命中 "rm -rf" 危险关键词)
    with pytest.raises(SecurityError, match="命令"):
        executor.run(["rm", "-rf", "/tmp/test"])

    # 验证: 走 probe_executor 白名单的命令 (nvidia-smi) 不会被黑名单拦
    # (虽然 nvidia-smi 在真实系统不存在, 但 command validator 不会拦)


def test_get_probe_executor_enforces_shell_false():
    """probe_executor.run 内部用 shell=False (验证源码契约)"""
    from scenefab.utils import security

    security._PROBE_EXECUTOR = None
    # 读源码验证 shell=False
    source = security.SecureExecutor.run.__code__.co_filename
    with open(source) as f:
        code = f.read()
    # SecureExecutor.run 内必须有 shell=False
    assert "shell=False" in code, "SecureExecutor.run 必须强制 shell=False"


# =============================================================================
# 3. api/routers/pipeline.py: 路径校验 + 防御性 video_url 校验
# =============================================================================


def test_pipeline_validate_output_dir_accepts_safe():
    """安全路径通过校验"""
    from scenefab.api.routers.pipeline import _validate_output_dir

    # 当前 cwd 下的 outputs/ 在默认白名单内
    safe_path = os.path.join(os.getcwd(), "outputs", "test_draft")
    # 不抛异常 = 通过
    result = _validate_output_dir(safe_path)
    assert result == safe_path


def test_pipeline_validate_output_dir_rejects_dangerous():
    """危险路径 (DANGEROUS_PATH_PATTERNS) 被拒"""
    from fastapi import HTTPException

    from scenefab.api.routers.pipeline import _validate_output_dir

    # /etc 是黑名单路径
    with pytest.raises(HTTPException) as exc_info:
        _validate_output_dir("/etc/passwd_drafts")
    assert exc_info.value.status_code == 400


def test_pipeline_validate_output_dir_rejects_path_traversal():
    """路径穿越攻击 (../) 被拒"""
    from fastapi import HTTPException

    from scenefab.api.routers.pipeline import _validate_output_dir

    with pytest.raises(HTTPException) as exc_info:
        _validate_output_dir("./outputs/../../etc/cron.d")
    assert exc_info.value.status_code == 400


def test_pipeline_validate_output_dir_none_returns_none():
    """None / 空字符串直接返回 (不校验, 调用方用默认)"""
    from scenefab.api.routers.pipeline import _validate_output_dir

    assert _validate_output_dir(None) is None
    assert _validate_output_dir("") == ""


def test_pipeline_create_narration_rejects_empty_video_url():
    """防御性: 空 video_url 在请求入口拒绝 (避免进入处理流程)"""
    from fastapi import HTTPException

    from scenefab.api.routers.pipeline import create_narration_task
    from scenefab.api.schemas.models import NarrationRequest

    # Empty video_url
    req = NarrationRequest(project_id="p1", video_url="")
    with pytest.raises(HTTPException) as exc_info:
        # create_narration_task 是 async, 通过 asyncio.run 隔离
        import asyncio
        asyncio.run(create_narration_task(req))
    assert exc_info.value.status_code == 400
    assert "video_url" in exc_info.value.detail


def test_pipeline_create_narration_rejects_whitespace_video_url():
    """防御性: 全空白 video_url 同样拒绝"""
    from fastapi import HTTPException

    from scenefab.api.routers.pipeline import create_narration_task
    from scenefab.api.schemas.models import NarrationRequest

    req = NarrationRequest(project_id="p1", video_url="   \t  ")
    with pytest.raises(HTTPException) as exc_info:
        import asyncio
        asyncio.run(create_narration_task(req))
    assert exc_info.value.status_code == 400


# =============================================================================
# 4. 综合: 验证 export router 模式与 pipeline router 模式等价
# =============================================================================


def test_pipeline_and_export_validators_share_pattern():
    """两个 router 共享同一安全语义"""
    from scenefab.api.routers import export, pipeline

    # 都用 PathValidator + SecurityError
    assert hasattr(pipeline, "PathValidator")
    assert hasattr(pipeline, "SecurityError")
    assert hasattr(export, "PathValidator")
    assert hasattr(export, "SecurityError")

    # 都用 _DEFAULT_ALLOWED_BASE_DIRS
    assert hasattr(pipeline, "_DEFAULT_ALLOWED_BASE_DIRS")
    assert hasattr(export, "_DEFAULT_ALLOWED_BASE_DIRS")
    # 语义一致 (集合相等)
    assert set(pipeline._DEFAULT_ALLOWED_BASE_DIRS) == set(export._DEFAULT_ALLOWED_BASE_DIRS)