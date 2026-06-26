#!/usr/bin/env python3
"""
回归测试: utils/security + secure_key_manager
收紧 except Exception 后, 文件 IO/Subprocess 错误仍正确处理, 但 RuntimeError/TypeError 不再被吞.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scenefab.utils.security import (
    SecurityCheckResult,
    SecureExecutor,
    SecureFileHandler,
    SecurityError,
)


# =============================================================================
# 1. utils/security.py - SecureExecutor
# =============================================================================


def test_secure_executor_timeout_raises_security_error():
    """subprocess.TimeoutExpired → SecurityError"""
    executor = SecureExecutor()

    # bypass 命令白名单 (mock CommandValidator.validate)
    with patch.object(executor.command_validator, "validate",
                      return_value=SecurityCheckResult(True, "ok")):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["echo"], timeout=1)):
            with pytest.raises(SecurityError, match="超时"):
                executor.run(["echo", "test"], timeout=1)


def test_secure_executor_subprocess_error_raises_security_error():
    """subprocess.SubprocessError (如 CalledProcessError) → SecurityError"""
    executor = SecureExecutor()

    # 用 CalledProcessError (subprocess 实际返回码非 0) 测试 SubprocessError 子类
    with patch.object(executor.command_validator, "validate",
                      return_value=SecurityCheckResult(True, "ok")):
        with patch("subprocess.run",
                   side_effect=subprocess.CalledProcessError(returncode=1, cmd=["echo"])):
            with pytest.raises(SecurityError, match="命令执行失败"):
                executor.run(["echo", "test"], timeout=5)


def test_secure_executor_filenotfound_error_raises_security_error():
    """FileNotFoundError (命令不存在) → SecurityError (FileNotFoundError 是 OSError, 非 SubprocessError)"""
    executor = SecureExecutor()

    with patch.object(executor.command_validator, "validate",
                      return_value=SecurityCheckResult(True, "ok")):
        with patch("subprocess.run", side_effect=FileNotFoundError("echo not found")):
            with pytest.raises(SecurityError, match="命令执行失败"):
                executor.run(["echo", "test"], timeout=5)


def test_secure_executor_runtime_error_propagates():
    """★诚实性: RuntimeError 不再被 SecurityError 包裹"""
    executor = SecureExecutor()

    with patch.object(executor.command_validator, "validate",
                      return_value=SecurityCheckResult(True, "ok")):
        with patch("subprocess.run", side_effect=RuntimeError("Code bug: bad state")):
            with pytest.raises(RuntimeError, match="Code bug"):
                executor.run(["echo", "test"], timeout=5)


# =============================================================================
# 2. utils/security.py - SecureFileHandler (用真实文件测)
# =============================================================================


def test_secure_file_handler_read_oserror_raises_security_error(tmp_path):
    """SecureFileHandler.read OSError → SecurityError"""
    handler = SecureFileHandler()

    # 先创建真实文件 (Path.stat 通过)
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    # 然后 mock open 抛 OSError
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        with pytest.raises(SecurityError):
            handler.read(str(test_file), category="document")


def test_secure_file_handler_write_oserror_raises_security_error(tmp_path):
    """SecureFileHandler.write OSError → SecurityError"""
    handler = SecureFileHandler()

    with patch("builtins.open", side_effect=OSError("Disk full")):
        with pytest.raises(SecurityError, match="文件写入失败"):
            handler.write(str(tmp_path / "test.txt"), "content")


# =============================================================================
# 3. secure_key_manager.py: 文件 IO 部分
# =============================================================================


def test_secure_key_get_file_based_key_oserror_falls_back():
    """文件读取 OSError → 降级生成新密钥"""
    from scenefab.secure_key_manager import SecureKeyManager

    mgr = SecureKeyManager(app_name="test_app_xyz_123")

    with patch.object(Path, "exists", return_value=True):
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            key = mgr._get_file_based_key()
            assert key is not None
            assert isinstance(key, bytes)
            assert len(key) == 44


def test_secure_key_get_encrypted_fernet_invalid_token():
    """Fernet decrypt 抛 InvalidToken (ValueError 子类) → log + return None"""
    from scenefab.secure_key_manager import SecureKeyManager
    from cryptography.fernet import Fernet

    mgr = SecureKeyManager(app_name="test_app_xyz_123")
    valid_key = Fernet.generate_key()
    mgr._encryption_key = valid_key

    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open"):
            with patch("cryptography.fernet.Fernet.decrypt",
                       side_effect=ValueError("Invalid token")):
                result = mgr._get_encrypted_key("nonexistent_provider")
                assert result is None


def test_secure_key_get_encrypted_runtime_error_propagates():
    """★诚实性: _get_encrypted_key 中 RuntimeError 不再被吞"""
    from scenefab.secure_key_manager import SecureKeyManager
    from cryptography.fernet import Fernet

    mgr = SecureKeyManager(app_name="test_app_xyz_123")
    valid_key = Fernet.generate_key()
    mgr._encryption_key = valid_key

    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open"):
            with patch("cryptography.fernet.Fernet.decrypt",
                       side_effect=RuntimeError("Code bug: bad decryption")):
                with pytest.raises(RuntimeError, match="Code bug"):
                    mgr._get_encrypted_key("nonexistent_provider")


def test_secure_key_save_key_file_oserror_logs_error():
    """_get_file_based_key save 时 OSError → log error + 降级生成 key"""
    from scenefab.secure_key_manager import SecureKeyManager

    mgr = SecureKeyManager(app_name="test_app_xyz_123")

    with patch.object(Path, "exists", return_value=False):
        with patch("builtins.open", side_effect=OSError("Disk full")):
            key = mgr._get_file_based_key()
            assert key is not None
            assert isinstance(key, bytes)
            assert len(key) == 44